"""Screen radar candidates using historical water and terrain slope."""
import json
import math
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling
from pipeline.core.preprocessing import read_aligned, write_raster

ROOT=Path(__file__).resolve().parents[1]


def convert_source(name):
    base=ROOT/'data/inputs/auxiliary'
    meta=json.loads((base/(name+'.json')).read_text())
    dtype={'Float32Array':'<f4','Uint8Array':'u1'}[meta['dtype']]
    array=np.fromfile(base/(name+'.bin'),dtype=dtype).reshape(meta['height'],meta['width'])
    if name.startswith('jrc'):
        array=np.where(array<=100,array,np.nan).astype('float32')
    else:array=array.astype('float32')
    profile=dict(driver='GTiff',width=meta['width'],height=meta['height'],count=1,
                 dtype='float32',crs=meta['crs'],transform=Affine(*meta['transform']))
    target=base/(name+'.tif');write_raster(target,array,profile)
    return target


def run():
    out=ROOT/'data/products/radar_rerun'
    dem_path=convert_source('dem_source_crop');water_path=convert_source('jrc_source_crop')
    with rasterio.open(out/'before_HH_db.tif') as ds:profile=ds.profile.copy()
    coarse=profile.copy()
    coarse.update(width=math.ceil(profile['width']/3),height=math.ceil(profile['height']/3),
                  transform=profile['transform']*Affine.scale(3,3))
    dem,_=read_aligned(dem_path,coarse)
    dy,dx=np.gradient(dem,30.,30.)
    slope=np.degrees(np.arctan(np.hypot(dx,dy))).astype('float32')
    slope_path=out/'slope_30m_degrees.tif';write_raster(slope_path,slope,coarse)
    aligned_slope,_=read_aligned(slope_path,profile)
    water,_=read_aligned(water_path,profile,categorical=True)
    known=np.isfinite(aligned_slope)&np.isfinite(water)
    write_raster(out/'water_occurrence_aligned.tif',water,profile)
    write_raster(out/'slope_aligned.tif',aligned_slope,profile)
    records=[]
    with rasterio.open(out/'candidate_middle_unvalidated.tif') as ds:original=ds.read(1)
    candidate=original==1
    area=abs(profile['transform'].a*profile['transform'].e)/1e6
    for limit in [3,5,10]:
        mask=candidate&known&(water<90)&(aligned_slope<=limit)
        records.append(dict(water_occurrence_limit=90,slope_limit_deg=limit,
                            pixels=int(mask.sum()),area_km2=float(mask.sum()*area)))
        if limit==5:
            raster=np.where((original!=255)&known,mask.astype('uint8'),255).astype('uint8')
            write_raster(out/'candidate_screened_unvalidated.tif',raster,profile,255)
    report=dict(status='unvalidated_rerun_separate_from_published_case',
                initial_pixels=int(candidate.sum()),missing_auxiliary_pixels=int((candidate&~known).sum()),
                historical_water_removed=int((candidate&known&(water>=90)).sum()),
                slope_removed_excluding_water=int((candidate&known&(water<90)&(aligned_slope>5)).sum()),
                sensitivity=records,
                method='JRC v1.5 nearest; DEM bilinear to 30 m UTM, gradient slope degrees, bilinear slope to 10 m; no post-screen size pruning.',
                source_metadata=['data/inputs/auxiliary/dem_source_crop.json','data/inputs/auxiliary/jrc_source_crop.json'],
                limitation='New public subsets retrieved 2026-11-15; not exact original Colab auxiliary files. No flood confirmation.')
    (out/'screening.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
