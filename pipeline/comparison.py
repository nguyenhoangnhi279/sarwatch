"""Compare the numerical rerun with the published candidate polygons."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from rasterio.warp import transform_geom
from shapely.geometry import shape, mapping
from shapely import make_valid
from app.server.data_loader import load_bundle

ROOT=Path(__file__).resolve().parents[1]


def run():
    out=ROOT/'data/products/radar_rerun'
    with rasterio.open(out/'candidate_screened_unvalidated.tif') as ds:
        pixels=ds.read(1);transform=ds.transform;crs=ds.crs
    _,geo,_,_=load_bundle((ROOT/'data/products/sarwatch_demo_bundle.zip').read_bytes())
    geoms=[transform_geom('EPSG:4326',crs,f['geometry']) for f in geo['features']]
    original=rasterize([(g,1) for g in geoms],out_shape=pixels.shape,transform=transform,dtype='uint8')==1
    valid=pixels!=255;rerun=pixels==1
    intersection=int((original&rerun&valid).sum());union=int(((original|rerun)&valid).sum())
    report=dict(task='product_agreement_NOT_flood_accuracy',original_pixels=int(original.sum()),
                rerun_pixels=int(rerun.sum()),common_intersection_pixels=intersection,
                common_union_pixels=union,jaccard=intersection/union,
                original_pixels_without_rerun_coverage=int((original&~valid).sum()),
                interpretation='Different documented threshold/support/connectivity and new auxiliary subsets; not independent validation.')
    (out/'product_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    features=[]
    for geometry,value in shapes(rerun.astype('uint8'),mask=rerun,transform=transform,connectivity=8):
        repaired=make_valid(shape(geometry))
        geographic=transform_geom(crs,'EPSG:4326',mapping(repaired))
        centre=shape(geographic).centroid
        features.append(dict(type='Feature',properties=dict(id=len(features)+1,
                             area_m2=float(repaired.area),longitude=centre.x,latitude=centre.y,
                             status='Unvalidated numerical rerun'),geometry=geographic))
    assert abs(sum(f['properties']['area_m2'] for f in features)-int(rerun.sum())*100)<.01
    (out/'rerun_candidates_unvalidated.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features)),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
