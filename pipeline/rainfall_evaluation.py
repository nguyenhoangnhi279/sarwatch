"""Operator-only verification against independent observed window totals.

CSV columns: snapshot,site,hours,observed_mm,observation_source
snapshot is the basename of an data/products/forecasts JSON file. The observed total
must cover exactly [retrieved_at,retrieved_at+hours*3600] at that site.
Do not substitute forecasts or reanalysis for station observations silently.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import time
from app.server.weather import accumulation, validate_forecast
from app.server.verification import scores


def evaluate(root, path, thresholds):
    groups = {5: [], 12: []}
    sources, seen, starts, ends = set(), set(), [], []
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            name = row['snapshot']
            if Path(name).name != name or not name.endswith('.json'):
                raise ValueError('Expected a snapshot basename')
            data = json.loads((root / 'data/products' / 'forecasts' / name).read_text(encoding='utf-8'))
            h = int(row['hours'])
            if h not in groups or row['site'] != data['site']:
                raise ValueError('Invalid horizon or site')
            key = (data['retrieved_at'], data['site'], h)
            if key in seen:
                raise ValueError('Duplicate verification pair')
            seen.add(key)
            start = data['retrieved_at']
            if start + h * 3600 > time.time():
                raise ValueError('Observation window is still in the future')
            observed = float(row['observed_mm'])
            if not math.isfinite(observed) or observed < 0 or not row['observation_source'].strip():
                raise ValueError('Independent observation and source required')
            forecast = accumulation(validate_forecast(data['data']), start, h)['mm']
            if forecast is None:
                raise ValueError('Incomplete forecast window')
            groups[h].append((forecast, observed))
            starts.append(start)
            ends.append(start+h*3600)
            sources.add(row['observation_source'])
    if not starts:
        raise ValueError('No observations')
    return {'status': 'evaluated', 'generated_at': int(time.time()),
            'observation_sources': sorted(sources), 'period_start': min(starts), 'period_end': max(ends),
            'note': 'Operator must verify spatial/temporal matching and independent provenance. Overlapping windows are not independent events. No flood skill implied.',
            'horizons': {str(h): scores(p, thresholds[h]) for h, p in groups.items() if p}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observations_csv')
    parser.add_argument('--threshold-5', type=float, required=True)
    parser.add_argument('--threshold-12', type=float, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root, args.observations_csv, {5: args.threshold_5, 12: args.threshold_12})
    output = root / 'data/products' / 'verification' / 'rainfall_metrics.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    print(output)
