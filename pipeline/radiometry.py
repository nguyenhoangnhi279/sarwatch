"""Summarize radar changes across persistent optical classes."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.ndimage import maximum_filter

ROOT=Path(__file__).resolve().parents[1]


def run():
    base=ROOT/'data/products/radar_rerun'
    with rasterio.open(base/'before_HH_db.tif') as ds:
        profile=ds.profile
    arrays=[]
    for day in ['16','26']:
        out=np.zeros((profile['height'],profile['width']),dtype='uint8')
        with rasterio.open(ROOT/'data/inputs/reference'/f'S2B_48QYD_202610{day}_0_L2A_scl.tif') as ds:
            reproject(ds.read(1),out,src_transform=ds.transform,src_crs=ds.crs,
                      dst_transform=profile['transform'],dst_crs=profile['crs'],
                      src_nodata=0,dst_nodata=0,resampling=Resampling.nearest)
        arrays.append(out)
    b,a=arrays;clear=np.isin(b,[4,5,6])&np.isin(a,[4,5,6])
    clear &= ~maximum_filter((~clear).astype('uint8'),size=13,mode='constant',cval=1).astype(bool)
    rows=[]
    for name,mask in [('persistent_vegetation',(b==4)&(a==4)),
                      ('persistent_bare_or_built',(b==5)&(a==5)),
                      ('persistent_water',(b==6)&(a==6))]:
        for ch in ['HH','HV']:
            with rasterio.open(base/f'delta_{ch}.tif') as ds:delta=ds.read(1)
            values=delta[mask&clear&np.isfinite(delta)]
            rows.append(dict(group=name,channel=ch,pixels=len(values),
                             delta_p05_median_p95_db=list(map(float,np.percentile(values,[5,50,95])))))
    report=dict(method='Persistent SCL classes, 60 m cloud/invalid buffer, NISAR 10 m grid',
                interpretation='Persistent optical class does not guarantee unchanged radar scattering. '
                  'Seasonality, moisture, wind and processing differences remain confounded; no automatic correction.',
                records=rows)
    (base/'radiometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
