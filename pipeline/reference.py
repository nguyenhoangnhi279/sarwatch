"""Compare radar candidates with dated Sentinel-2 reference observations."""
import base64
import csv
import io
import json
import math
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.features import rasterize
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
from rasterio.transform import array_bounds, Affine
from shapely.geometry import shape, box, mapping
from pipeline.core.impact_analysis import project
from app.server.data_loader import load_bundle

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'data/inputs/reference'
OUT=ROOT/'data/products'/'validation'
NISAR_TIMES=['2026-10-15T11:21:40Z','2026-10-27T11:21:40Z']


def dilate(mask,radius):
    """Conservative square cloud/shadow boundary buffer, in source pixels."""
    if not radius:return mask.copy()
    padded=np.pad(mask,radius,constant_values=True)
    result=np.zeros_like(mask)
    for dy in range(2*radius+1):
        for dx in range(2*radius+1):
            result |= padded[dy:dy+mask.shape[0],dx:dx+mask.shape[1]]
    return result


def optical_masks(before,after,buffer_pixels=3):
    clear_before=np.isin(before,[4,5,6]);clear_after=np.isin(after,[4,5,6])
    valid=~dilate(~clear_before|~clear_after,buffer_pixels)
    return valid, valid&(after==6)&np.isin(before,[4,5]), valid&(after==6)&(before==6)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    meta,geo,_,_=load_bundle((ROOT/'data/products'/'sarwatch_demo_bundle.zip').read_bytes())
    impact=json.loads((ROOT/'data/products'/'impact'/'review_analysis.json').read_text(encoding='utf-8'))
    catalogue=json.loads((REF/'sentinel2_search.json').read_text(encoding='utf-8'))
    scenes=[next(f for f in catalogue['features'] if f['id']==f'S2B_48QYD_202610{day}_0_L2A') for day in ('16','26')]
    bounds=json.loads((REF/'utm_bounds.json').read_text())
    arrays=[]
    for scene in scenes:
        with rasterio.open(REF/(scene['id']+'_scl.tif')) as ds:
            w=from_bounds(*bounds,ds.transform)
            col,row=math.floor(w.col_off),math.floor(w.row_off)
            window=Window(col,row,math.ceil(w.col_off+w.width)-col,math.ceil(w.row_off+w.height)-row)
            arrays.append(ds.read(1,window=window))
            transform=ds.window_transform(window)
    before,after=arrays
    valid,new_water,existing=optical_masks(before,after,3)
    geoms=[project(shape(f['geometry'])) for f in geo['features']]
    predicted=rasterize([(mapping(g),1) for g in geoms],out_shape=before.shape,transform=transform,fill=0,dtype='uint8')>0
    # Explicitly centre-rasterized comparison grid, not a flood-accuracy test.
    counts={name:int(np.count_nonzero(mask)) for name,mask in {
        'both_change':valid&predicted&new_water,
        'nisar_only':valid&predicted&~new_water,
        'optical_only':valid&~predicted&new_water,
        'neither':valid&~predicted&~new_water}.items()}
    cache,records={},[]
    for feature,geom in zip(geo['features'],geoms):
        w=from_bounds(*geom.bounds,transform)
        r0,r1=max(0,math.floor(w.row_off)),min(before.shape[0],math.ceil(w.row_off+w.height))
        c0,c1=max(0,math.floor(w.col_off)),min(before.shape[1],math.ceil(w.col_off+w.width))
        area_clear,area_new,area_existing=0.,0.,0.
        for row in range(r0,r1):
            for col in range(c0,c1):
                if not valid[row,col]:continue
                key=(row,col)
                if key not in cache:
                    x,y=transform*(col,row)
                    cache[key]=box(x,y-20,x+20,y)
                area=geom.intersection(cache[key]).area
                area_clear+=area
                if new_water[row,col]:area_new+=area
                if existing[row,col]:area_existing+=area
        status='optical_new_water_overlap' if area_new>1 else 'existing_water_only' if area_existing>1 else 'no_new_water_on_clear_part' if area_clear>1 else 'obscured'
        records.append({'id':str(feature['properties']['id']),
                        'crosscheck_status':status,'clear_fraction':min(1,area_clear/geom.area),
                        'clear_area_m2':area_clear,'new_water_overlap_m2':area_new,'existing_water_overlap_m2':area_existing,
                        'new_water_fraction_of_clear':area_new/area_clear if area_clear else None,
                        'validated_inundation':False})
    sensitivity=[]
    for radius in [0,3,5]:
        clear,nw,_=optical_masks(before,after,radius)
        sensitivity.append({'buffer_metres':radius*20,'clear_candidate_grid_fraction':float(clear[predicted].mean()),
                            'overlapping_new_water_grid_cells':int(np.count_nonzero(clear&predicted&nw))})
    images={}
    native_rgb={}
    for date,scene in zip(['before','after'],scenes):
        data=json.loads((REF/(scene['id']+'_rgb.json')).read_text())
        rgb=np.fromfile(REF/(scene['id']+'_rgb.bin'),dtype='uint8').reshape(data['height'],data['width'],3)
        native_rgb[date]=rgb
        native_transform=Affine(*data['transform'])
        source_bounds=array_bounds(data['height'],data['width'],native_transform)
        dst,w,h=calculate_default_transform(32648,3857,data['width'],data['height'],*source_bounds)
        scale=min(1,1400/max(w,h));width,height=round(w*scale),round(h*scale)
        dst*=Affine.scale(w/width,h/height)
        output=np.zeros((height,width,3),dtype='uint8')
        for band in range(3):
            reproject(rgb[:,:,band],output[:,:,band],src_transform=native_transform,src_crs=32648,dst_transform=dst,dst_crs=3857,resampling=Resampling.bilinear)
        picture=Image.fromarray(output)
        buffer=io.BytesIO();picture.save(buffer,format='JPEG',quality=87)
        (OUT/f'sentinel2_{date}.jpg').write_bytes(buffer.getvalue())
        west,south,east,north=transform_bounds(3857,4326,*array_bounds(height,width,dst))
        images[date]={'data_url':'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii'),
                      'bounds':[[south,west],[north,east]],'date':scene['properties']['datetime']}
    summary={'candidates_checked':len(records),
             'with_some_clear_reference':sum(r['clear_area_m2']>1 for r in records),
             'with_no_clear_reference':sum(r['clear_area_m2']<=1 for r in records),
             'with_any_new_water_overlap':sum(r['new_water_overlap_m2']>1 for r in records),
             'with_existing_water_only':sum(r['crosscheck_status']=='existing_water_only' for r in records),
             'with_no_new_water_on_clear_part':sum(r['crosscheck_status']=='no_new_water_on_clear_part' for r in records),
             'candidate_clear_area_km2':sum(r['clear_area_m2'] for r in records)/1e6,
             'candidate_new_water_overlap_km2':sum(r['new_water_overlap_m2'] for r in records)/1e6,
             'comparison_grid_counts':counts,'independently_confirmed_flood_area_km2':None}
    selected=[]
    ordered_ids=[str(f['properties']['id']) for f in impact['geojson']['features'][:6]]
    ordered_ids += [r['id'] for r in sorted(records,key=lambda r:r['new_water_overlap_m2'],reverse=True)[:3]]
    ordered_ids += [r['id'] for r in records if r['crosscheck_status']=='obscured'][:3]
    seen=set()
    for ident in ordered_ids:
        if ident not in seen:selected.append(ident);seen.add(ident)
    by_id={str(f['properties']['id']):g for f,g in zip(geo['features'],geoms)}
    font=ImageFont.truetype(str(ROOT/'app/web'/'fonts'/'be-vietnam-0.ttf'),15)
    native_data=json.loads((REF/(scenes[0]['id']+'_rgb.json')).read_text())
    nt=Affine(*native_data['transform'])
    for sheet in range(math.ceil(len(selected)/3)):
        chunk=selected[sheet*3:(sheet+1)*3]
        canvas=Image.new('RGB',(800,310*len(chunk)),(246,247,242));draw=ImageDraw.Draw(canvas)
        for index,ident in enumerate(chunk):
            geom=by_id[ident];xmin,ymin,xmax,ymax=geom.bounds
            pad=max(150,(max(xmax-xmin,ymax-ymin)*.25));size=max(xmax-xmin,ymax-ymin)+2*pad
            cx,cy=geom.centroid.coords[0];extent=(cx-size/2,cy-size/2,cx+size/2,cy+size/2)
            x0,y1=~nt*(extent[0],extent[3]);x1,y0=~nt*(extent[2],extent[1])
            frame=(int(x0),int(y1),int(x1),int(y0))
            ytop=index*310
            draw.text((12,ytop+5),'Vùng '+ident+' · Sentinel-2 (lệch thời điểm NISAR)',font=font,fill='#24412b')
            for column,date in enumerate(['before','after']):
                chip=Image.fromarray(native_rgb[date]).crop(frame).resize((375,250),Image.Resampling.NEAREST)
                painter=ImageDraw.Draw(chip)
                parts=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
                for part in parts:
                    if part.geom_type!='Polygon':continue
                    for ring in [part.exterior,*part.interiors]:
                        points=[((x-extent[0])/size*375,(extent[3]-y)/size*250) for x,y in ring.coords]
                        painter.line(points,fill='#ffcb56',width=2)
                canvas.paste(chip,(12+column*395,ytop+34))
                draw.text((12+column*395,ytop+286),'16/10/2026' if date=='before' else '26/10/2026',font=font,fill='#24412b')
        canvas.save(OUT/f'optical_review_sheet_{sheet+1}.jpg',quality=94)
    payload={'schema_version':1,'status':'independent_source_crosscheck_not_ground_truth',
             'analysis_version':impact['analysis_version'],'created_at':datetime.now(timezone.utc).isoformat(),
             'summary':summary,'records':records,'images':images,'sensitivity':sensitivity,
             'sources':[{'id':f['id'],'datetime':f['properties']['datetime'],'scl':f['assets']['scl']['href'],
                         'visual':f['assets']['visual']['href'],'licence':'Copernicus Sentinel data 2026',
                         'offset_from_nisar_hours':(datetime.fromisoformat(f['properties']['datetime'].replace('Z','+00:00'))-datetime.fromisoformat(t.replace('Z','+00:00'))).total_seconds()/3600}
                        for f,t in zip(scenes,NISAR_TIMES)],
             'protocol':{'clear_scl_classes':[4,5,6],'water_scl_class':6,'extra_cloud_shadow_buffer_metres':60,
                         'new_water_definition':'SCL before 4/5 -> after 6 on jointly clear pixels',
                         'region_overlap_method':'exact polygon/cell intersection area in EPSG:32648'},
             'visual_inspection_queue':selected,
             'limitations':['Reference dates differ by +16.2 h and -31.8 h from NISAR; transient flooding may differ.',
                            'SCL is an automatic atmospheric-processing classification, not an independently surveyed flood map.',
                            'Clouds, shadows, unclassified and NoData are excluded; obscured parts remain unknown.',
                            'No new optical water on a clear part does not prove no flood at the NISAR acquisition.',
                            'Full NISAR valid-observation raster is absent, so optical-only cells cannot be called missed floods.',
                            'Agreement counts are not flood accuracy; no validated inundation or F1/IoU claim is made.']}
    (OUT/'optical_crosscheck.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    with (OUT/'optical_crosscheck.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    (ROOT/'app/web'/'reference-data.js').write_text('globalThis.SARWatchReference='+json.dumps(payload,ensure_ascii=True,allow_nan=False,separators=(',',':'))+';\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':build()
