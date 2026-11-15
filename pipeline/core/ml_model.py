"""Spatial splits and classification metrics for optical water-proxy labels."""
import numpy as np
from sklearn.metrics import confusion_matrix


def spatial_split(x, y, block_m=2000, guard_m=100):
    """Same geographic block gets same split at both dates; exclude boundaries."""
    bx=np.floor(x/block_m).astype('int64');by=np.floor(y/block_m).astype('int64')
    # Fixed deterministic hash independent of features and labels.
    fold=((bx*73856093)^(by*19349663)^42)%5
    inside=((x%block_m>=guard_m)&(x%block_m<block_m-guard_m)&
            (y%block_m>=guard_m)&(y%block_m<block_m-guard_m))
    result=np.where(fold==0,2,np.where(fold==1,1,0)).astype('int8')
    return np.where(inside,result,-1).astype('int8')


def scores(truth, prediction):
    tn,fp,fn,tp=map(int,confusion_matrix(truth,prediction,labels=[0,1]).ravel())
    ratio=lambda a,b:float(a/b) if b else None
    return dict(samples=len(truth),water_samples=int(np.sum(truth)),
                tp=tp,fp=fp,fn=fn,tn=tn,precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),
                f1=ratio(2*tp,2*tp+fp+fn),iou=ratio(tp,tp+fp+fn))
