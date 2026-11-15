"""Process the four downloaded GCOV radar subsets."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from pipeline.core.preprocessing import read_aligned, smooth_power_db, write_raster
from pipeline.core.change_detection import otsu_threshold, detect

ROOT=Path(__file__).resolve().parents[1]


def run():
    out=ROOT/'data/products'/'radar_rerun';out.mkdir(parents=True,exist_ok=True)
    arrays={}; hashes={}; profile=None
    for date in ('before','after'):
        for channel in ('HH','HV'):
            key=date+'_'+channel;path=ROOT/'data/inputs/raw'/(key+'.tif')
            power,profile=read_aligned(path,profile)
            hashes[key]=hashlib.sha256(path.read_bytes()).hexdigest()
            arrays[key]=smooth_power_db(power)
            write_raster(out/(key+'_db.tif'),arrays[key],profile)
    b,a,bv,av=[arrays[k] for k in ('before_HH','after_HH','before_HV','after_HV')]
    valid=np.logical_and.reduce([np.isfinite(x) for x in (b,a,bv,av)])
    threshold=otsu_threshold(np.concatenate([b[valid],a[valid]]))
    area=abs(profile['transform'].a*profile['transform'].e-profile['transform'].b*profile['transform'].d)
    if not profile['crs'].is_projected or profile['crs'].linear_units != 'metre':
        raise ValueError('Area requires a projected CRS in metres.')
    settings=[]
    for name,hh,hv in [('loose',-1.,-.5),('middle',-1.5,-.75),('strict',-2.,-1.)]:
        mask,_=detect(b,a,bv,av,threshold,hh,hv)
        output=np.where(valid,mask.astype('uint8'),255).astype('uint8')
        write_raster(out/('candidate_'+name+'_unvalidated.tif'),output,profile,255)
        settings.append(dict(setting=name,hh_limit_db=hh,hv_limit_db=hv,
                             pixels=int(mask.sum()),area_km2=float(mask.sum()*area/1e6)))
    qc={}
    for ch in ('HH','HV'):
        delta=arrays['after_'+ch]-arrays['before_'+ch]
        qc[ch]=dict(zip(('p05','median','p95'),map(float,np.percentile(delta[valid],[5,50,95]))))
        write_raster(out/('delta_'+ch+'.tif'),np.where(valid,delta,np.nan).astype('float32'),profile)
    write_raster(out/'valid_overlap.tif',valid.astype('uint8'),profile,255)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='unvalidated_rerun',
                raw_sha256=hashes,crs=str(profile['crs']),shape=list(b.shape),pixel_area_m2=area,
                valid_pixels=int(valid.sum()),valid_percent=float(100*valid.mean()),
                filter=dict(size=5,domain='linear power',minimum_support=.8,boundary='constant missing',
                            invalid_centre_preserved=True),otsu_pooled_hh_db=threshold,
                delta_db=qc,settings=settings,
                differences_from_original=['Explicit conservative filter support and 8-connected patches.',
                  'JRC/DEM screening is separate: screen_radar.py uses newly documented public subsets.',
                  'Different processing-maturity scenes; no assumed radiometric correction.',
                  'Do not replace the published case or claim replication of 9.3045 km2.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
