"""Detect open-water transitions from multitemporal radar backscatter."""
import numpy as np
from scipy.ndimage import label


def otsu_threshold(values, bins=256):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    if not len(values) or np.min(values) == np.max(values):
        raise ValueError('Otsu requires non-constant finite observations.')
    histogram, edges = np.histogram(values, bins=bins)
    centres = (edges[:-1]+edges[1:])/2
    weight = np.cumsum(histogram).astype('float64')
    moment = np.cumsum(histogram*centres)
    left = moment / np.maximum(weight, 1)
    right = (moment[-1]-moment) / np.maximum(weight[-1]-weight, 1)
    score = weight*(weight[-1]-weight)*(left-right)**2
    return float(centres[np.argmax(score[:-1])])


def remove_small(mask, min_pixels=25):
    regions, _ = label(mask, structure=np.ones((3,3), dtype='uint8'))
    counts = np.bincount(regions.ravel())
    keep = counts >= min_pixels
    keep[0] = False
    return keep[regions]


def detect(before_hh, after_hh, before_hv, after_hv, threshold,
           hh_limit=-1.5, hv_limit=-0.75, min_pixels=25):
    valid = np.logical_and.reduce([np.isfinite(x) for x in
                                   (before_hh, after_hh, before_hv, after_hv)])
    mask = (valid & (before_hh > threshold) & (after_hh <= threshold)
            & (after_hh-before_hh <= hh_limit) & (after_hv-before_hv <= hv_limit))
    return remove_small(mask, min_pixels), valid
