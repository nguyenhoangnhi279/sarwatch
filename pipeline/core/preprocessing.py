"""GCOV processing: filter positive linear power before conversion to dB."""
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter
from rasterio.warp import reproject, Resampling


def read_aligned(path, reference=None, categorical=False):
    with rasterio.open(path) as ds:
        data = ds.read(1, masked=True).astype('float32').filled(np.nan)
        profile = ds.profile.copy()
        if reference is None:
            return data, profile
        same = (ds.crs == reference['crs'] and ds.transform == reference['transform']
                and ds.width == reference['width'] and ds.height == reference['height'])
        if same:
            return data, reference.copy()
        output = np.full((reference['height'], reference['width']), np.nan, dtype='float32')
        reproject(data, output, src_transform=ds.transform, src_crs=ds.crs,
                  dst_transform=reference['transform'], dst_crs=reference['crs'],
                  src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=Resampling.nearest if categorical else Resampling.bilinear)
        return output, reference.copy()


def smooth_power_db(power, size=5, min_support=0.8):
    """NaN-safe mean: invalid centres stay invalid, >=80% window support."""
    if size < 1 or size % 2 != 1 or not 0 < min_support <= 1:
        raise ValueError('Use a positive odd window and support in (0,1].')
    valid = np.isfinite(power) & (power > 0)
    weights = uniform_filter(valid.astype('float64'), size=size, mode='constant', cval=0)
    numerator = uniform_filter(np.where(valid, power, 0).astype('float64'), size=size,
                               mode='constant', cval=0)
    mean = np.divide(numerator, weights, out=np.zeros_like(numerator), where=weights > 0)
    keep = valid & (weights >= min_support - 1e-12) & (mean > 0)
    output = np.full(power.shape, np.nan, dtype='float32')
    output[keep] = 10 * np.log10(mean[keep])
    return output


def write_raster(path, data, profile, nodata=np.nan):
    profile = profile.copy()
    profile.update(driver='GTiff', count=1, dtype=str(data.dtype), nodata=nodata,
                   compress='deflate', tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(path, 'w', **profile) as ds:
        ds.write(data, 1)
