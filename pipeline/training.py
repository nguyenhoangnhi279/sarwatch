"""Train and evaluate a water classifier using spatially separated blocks."""
import json
import sys
import hashlib
import sklearn
from pathlib import Path
import joblib
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from scipy.ndimage import maximum_filter
from sklearn.ensemble import RandomForestClassifier
from pipeline.core.ml_model import spatial_split, scores
from pipeline.core.change_detection import otsu_threshold

ROOT=Path(__file__).resolve().parents[1]


def run():
    rng=np.random.default_rng(42);tables=[];dates=[]
    for date,day in [('before','16'),('after','26')]:
        channels=[]
        for ch in ['HH','HV']:
            with rasterio.open(ROOT/'data/products/radar_rerun'/f'{date}_{ch}_db.tif') as ds:
                # Analysis uses a 20 m grid; bilinear averages neighbouring log values
                # only for model features, after scientific power-domain filtering.
                height,width=(ds.height+1)//2,(ds.width+1)//2
                transform=ds.transform*Affine.scale(2,2)
                array=np.full((height,width),np.nan,dtype='float32')
                reproject(ds.read(1),array,src_transform=ds.transform,src_crs=ds.crs,
                          dst_transform=transform,dst_crs=ds.crs,src_nodata=np.nan,
                          dst_nodata=np.nan,resampling=Resampling.bilinear)
                crs=ds.crs;channels.append(array)
        scl=np.zeros((height,width),dtype='uint8')
        with rasterio.open(ROOT/'data/inputs/reference'/f'S2B_48QYD_202610{day}_0_L2A_scl.tif') as ds:
            reproject(ds.read(1),scl,src_transform=ds.transform,src_crs=ds.crs,
                      dst_transform=transform,dst_crs=crs,src_nodata=0,dst_nodata=0,
                      resampling=Resampling.nearest)
        clear=np.isin(scl,[4,5,6])
        clear &= ~maximum_filter((~clear).astype('uint8'),size=7,mode='constant',cval=1).astype(bool)
        hh,hv=channels
        valid=clear&np.isfinite(hh)&np.isfinite(hv)
        rows,cols=np.where(valid)
        x=transform.c+(cols+.5)*transform.a;y=transform.f+(rows+.5)*transform.e
        split=spatial_split(x,y)
        selected=split>=0;rows,cols,split=rows[selected],cols[selected],split[selected]
        features=np.column_stack([hh[rows,cols],hv[rows,cols],hh[rows,cols]-hv[rows,cols]])
        truth=(scl[rows,cols]==6).astype('uint8')
        block_ids=(np.floor(x[selected]/2000).astype('int64')*100000+
                   np.floor(y[selected]/2000).astype('int64'))
        tables.append((features,truth,split,block_ids));dates.append(dict(nisar=date,sentinel2_day=day,
                usable_pixels=len(truth),water_pixels=int(truth.sum())))
    X=np.concatenate([t[0] for t in tables]);y=np.concatenate([t[1] for t in tables]);split=np.concatenate([t[2] for t in tables])
    blocks=np.concatenate([t[3] for t in tables])
    date_index=np.concatenate([np.full(len(t[1]),i,dtype='uint8') for i,t in enumerate(tables)])
    selection={}
    for key,fold in [('train',0),('validation',1),('test',2)]:
        indices=np.flatnonzero(split==fold)
        cap=120000 if fold==0 else 100000
        selection[key]=rng.choice(indices,min(cap,len(indices)),replace=False)
        if len(np.unique(y[selection[key]]))<2:raise ValueError('Both proxy classes required in every split.')
    train,val,test=[selection[k] for k in ['train','validation','test']]
    block_sets=[set(blocks[v]) for v in (train,val,test)]
    assert not (block_sets[0]&block_sets[1] or block_sets[0]&block_sets[2] or block_sets[1]&block_sets[2])
    if '--evaluate-existing' in sys.argv:
        model=joblib.load(ROOT/'data/products/ml/water_proxy_rf.joblib')['model']
    else:
        model=RandomForestClassifier(n_estimators=100,max_depth=14,min_samples_leaf=10,
                                    class_weight='balanced_subsample',n_jobs=2,random_state=42)
        model.fit(X[train],y[train])
    validation=model.predict_proba(X[val])[:,1]
    choices=[(scores(y[val],validation>=threshold)['iou'] or 0,float(threshold))
             for threshold in np.arange(.1,.91,.05)]
    _,threshold=max(choices)
    pred=model.predict_proba(X[test])[:,1]>=threshold
    baseline_threshold=otsu_threshold(X[train,0])
    baseline=X[test,0]<=baseline_threshold
    group_ids=np.unique(blocks[test]);confusions=[]
    for group in group_ids:
        use=blocks[test]==group
        pair=[]
        for p in (pred,baseline):
            s=scores(y[test][use],p[use]);pair.append([s['tp'],s['fp'],s['fn']])
        confusions.append(pair)
    confusions=np.asarray(confusions)
    boot_rng=np.random.default_rng(2026);bootstrap=[]
    for _ in range(1000):
        counts=confusions[boot_rng.integers(0,len(group_ids),len(group_ids))].sum(axis=0)
        iou=counts[:,0]/counts.sum(axis=1)
        bootstrap.append([iou[0],iou[1],iou[0]-iou[1]])
    intervals=np.percentile(bootstrap,[2.5,97.5],axis=0)
    report=dict(task='open_water_proxy_agreement_NOT_flood_accuracy',seed=42,
                sklearn_version=sklearn.__version__,
                raw_radar_sha256=json.loads((ROOT/'data/products/radar_rerun/report.json').read_text())['raw_sha256'],
                reference_scl_sha256={day:hashlib.sha256((ROOT/'data/inputs/reference'/f'S2B_48QYD_202610{day}_0_L2A_scl.tif').read_bytes()).hexdigest() for day in ['16','26']},
                features=['filtered_HH_dB','filtered_HV_dB','HH_minus_HV_dB'],
                proxy='Sentinel-2 SCL 6 versus 4/5; other classes excluded with 60 m boundary buffer',
                split='2 km geographic blocks; same split both dates; exclude 100 m block borders',
                sample_counts={k:len(v) for k,v in selection.items()},dates=dates,
                spatial_block_counts={k:len(np.unique(blocks[v])) for k,v in selection.items()},
                per_date_test={date:scores(y[test][date_index[test]==i],pred[date_index[test]==i])
                               for i,date in enumerate(['before','after'])},
                bootstrap_95=dict(method='1000 paired resamples of held-out 2 km blocks, seed 2026; descriptive, within-case only',
                                  rf_iou=list(map(float,intervals[:,0])),
                                  otsu_iou=list(map(float,intervals[:,1])),
                                  iou_difference=list(map(float,intervals[:,2]))),
                threshold_selection='maximum validation IoU on fixed 0.10:0.05:0.90 grid',
                threshold=threshold,baseline_train_otsu_db=baseline_threshold,
                test_random_forest=scores(y[test],pred),test_otsu=scores(y[test],baseline),
                feature_importance=dict(zip(['HH','HV','HH-HV'],map(float,model.feature_importances_))),
                limitations=['Not independent flood ground truth; SCL is an automated weak label.',
                  'Reference timing differs by +16.2 and -31.8 hours from NISAR.',
                  'One small AOI and two dates; not generalization to new events.',
                  'Pixel counts are not independent observations; water labels include coastal/open water.',
                  'Class-balanced model scores are not calibrated flood probabilities.',
                  'Do not replace candidate polygons or operational warnings with this experiment.'])
    out=ROOT/'data/products/ml';out.mkdir(parents=True,exist_ok=True)
    joblib.dump(dict(model=model,threshold=threshold,report=report),out/'water_proxy_rf.joblib')
    (out/'evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
