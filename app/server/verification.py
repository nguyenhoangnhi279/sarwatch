"""Compute verification metrics for matched forecast and observation pairs."""
import math


def scores(pairs, threshold):
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError('Threshold must be positive and finite')
    if not pairs:
        raise ValueError('No independent observation pairs')
    if any(not math.isfinite(v) or v < 0 for pair in pairs for v in pair):
        raise ValueError('Rainfall must be finite and nonnegative')
    errors = [f-o for f, o in pairs]
    hit = sum(f >= threshold and o >= threshold for f, o in pairs)
    false = sum(f >= threshold and o < threshold for f, o in pairs)
    miss = sum(f < threshold and o >= threshold for f, o in pairs)
    divide = lambda n, d: n/d if d else None
    return {'n': len(pairs), 'threshold_mm': threshold,
            'MAE_mm': sum(abs(e) for e in errors)/len(errors),
            'RMSE_mm': math.sqrt(sum(e*e for e in errors)/len(errors)),
            'bias_mm': sum(errors)/len(errors), 'hits': hit, 'false_alarms': false, 'misses': miss,
            'POD': divide(hit, hit+miss), 'FAR': divide(false, hit+false),
            'CSI': divide(hit, hit+false+miss)}
