"""Fixed-seed, stratified optical controls outside NISAR candidate polygons.

These are inspection controls, not randomly sampled flood ground truth.
"""
from pathlib import Path
import json,math
import numpy as np
import rasterio
from rasterio.windows import from_bounds,Window
from rasterio.features import rasterize
from rasterio.transform import Affine
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape,mapping
from pipeline.core.impact_analysis import project,TO_LONLAT
from pipeline.reference import optical_masks

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'data/inputs/reference';OUT=ROOT/'data/products'/'validation'
refs=[]
for day in ['16','26']:
    with rasterio.open(REF/f'S2B_48QYD_202610{day}_0_L2A_scl.tif') as ds:
        w=from_bounds(*json.loads((REF/'utm_bounds.json').read_text()),ds.transform)
        col,row=math.floor(w.col_off),math.floor(w.row_off)
        win=Window(col,row,math.ceil(w.col_off+w.width)-col,math.ceil(w.row_off+w.height)-row)
        refs.append(ds.read(1,window=win));t=ds.window_transform(win)
geo=json.loads((ROOT/'data/products'/'impact'/'review_candidates.geojson').read_text(encoding='utf-8'))
pred=rasterize([(mapping(project(shape(f['geometry']))),1) for f in geo['features']],out_shape=refs[0].shape,transform=t,dtype='uint8')>0
clear,new,_=optical_masks(*refs)
groups={'stable_water':clear&(refs[0]==6)&(refs[1]==6)&~pred,
        'stable_land':clear&np.isin(refs[0],[4,5])&np.isin(refs[1],[4,5])&~pred,
        'optical_new_water_outside_candidates':new&~pred,
        'obscured':~clear&~pred}
rng=np.random.default_rng(42);records=[]
for name,mask in groups.items():
    locations=np.argwhere(mask)
    for number,index in enumerate(rng.choice(len(locations),2,replace=False)):
        row,col=map(int,locations[index]);x,y=t*(col+.5,row+.5);lon,lat=TO_LONLAT(x,y)
        records.append({'id':name+'_'+str(number+1),'stratum':name,'row':row,'col':col,
                        'longitude':lon,'latitude':lat,'scl_before':int(refs[0][row,col]),
                        'scl_after':int(refs[1][row,col]),'nisar_candidate_at_grid_center':False,
                        'interpretation':'Optical inspection control; not a missed-flood or correct-negative label.'})
font=ImageFont.truetype(str(ROOT/'app/web'/'fonts'/'be-vietnam-0.ttf'),14)
for sheet in range(4):
    canvas=Image.new('RGB',(800,620),(246,247,242));draw=ImageDraw.Draw(canvas)
    for r,record in enumerate(records[sheet*2:(sheet+1)*2]):
        ytop=r*310;draw.text((12,ytop+5),record['id'],font=font,fill='#24412b')
        for c,day in enumerate(['16','26']):
            meta=json.loads((REF/f'S2B_48QYD_202610{day}_0_L2A_rgb.json').read_text())
            rgb=np.fromfile(REF/f'S2B_48QYD_202610{day}_0_L2A_rgb.bin',dtype='uint8').reshape(meta['height'],meta['width'],3)
            x,y=t*(record['col']+.5,record['row']+.5);col,row=~Affine(*meta['transform'])*(x,y)
            chip=Image.fromarray(rgb).crop((int(col-25),int(row-25),int(col+25),int(row+25))).resize((375,250),Image.Resampling.NEAREST)
            d=ImageDraw.Draw(chip);d.ellipse((182,120,192,130),outline='#ffce65',width=2)
            canvas.paste(chip,(12+c*395,ytop+34));draw.text((12+c*395,ytop+286),day+'/10/2026',font=font,fill='#24412b')
    canvas.save(OUT/f'noncandidate_controls_{sheet+1}.jpg',quality=94)
(OUT/'noncandidate_controls.json').write_text(json.dumps({'seed':42,'sampling':'two per optical stratum, not representative accuracy sampling','records':records},ensure_ascii=False,indent=2),encoding='utf-8')
print('Created 8 outside-candidate inspection controls; no ground-truth labels assigned.')
