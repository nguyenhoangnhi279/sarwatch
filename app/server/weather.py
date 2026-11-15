"""Fetch, cache and archive hourly provider forecasts."""
import json
import math
from pathlib import Path
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SITES = {
    'hue': ('Trung tâm Huế', 16.4637, 107.5909),
    'northwest': ('Điểm khảo sát tây bắc Huế', 16.54, 107.50),
    'coast': ('Điểm khảo sát ven biển', 16.53, 107.65),
    'south': ('Điểm khảo sát phía nam', 16.36, 107.65),
}


def forecast_url(site='hue'):
    _, lat, lon = SITES[site]
    return 'https://api.open-meteo.com/v1/forecast?' + urlencode({
        'latitude': lat, 'longitude': lon, 'hourly': 'precipitation',
        'models': 'ecmwf_ifs', 'forecast_days': 3,
        'timezone': 'Asia/Ho_Chi_Minh', 'timeformat': 'unixtime',
    })


def validate_forecast(data):
    if data.get('hourly_units', {}).get('precipitation') != 'mm':
        raise ValueError('Unexpected precipitation units')
    hourly = data['hourly']
    times, values = hourly['time'], hourly['precipitation']
    if not times or len(times) != len(values):
        raise ValueError('Incomplete hourly arrays')
    if any(not isinstance(t, (int, float)) or not math.isfinite(t) for t in times):
        raise ValueError('Invalid timestamps')
    if any(b-a != 3600 for a, b in zip(times, times[1:])):
        raise ValueError('Expected consecutive hourly intervals')
    if any(v is not None and (not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0) for v in values):
        raise ValueError('Invalid precipitation')
    return data


def accumulation(data, start, hours):
    """Precipitation at timestamp t covers (t-3600,t]; prorate edge hours."""
    end = start + hours * 3600
    amount, coverage = 0.0, 0
    for t, value in zip(data['hourly']['time'], data['hourly']['precipitation']):
        overlap = max(0, min(t, end) - max(t-3600, start))
        if overlap and value is not None:
            amount += value * overlap / 3600
            coverage += overlap
    return {'hours': hours, 'start': start, 'end': end,
            'mm': round(amount, 3) if coverage == hours * 3600 else None,
            'coverage_fraction': coverage / (hours * 3600)}


class WeatherStore:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.cache = {}

    def collect_forever(self):
        """Collect while the server runs, even when nobody opens the page."""
        while True:
            for site in SITES:
                try:
                    self.current(site)
                except (OSError, ValueError, KeyError, TypeError):
                    # Failed retrievals must not be archived as valid forecasts.
                    pass
            time.sleep(900)

    def current(self, site='hue'):
        if site not in SITES:
            raise ValueError('Unknown site')
        with self.lock:
            now = int(time.time())
            cached = self.cache.get(site)
            if not cached or now - cached['retrieved_at'] >= 900:
                req = Request(forecast_url(site), headers={'User-Agent': 'SARWatch-research/1.0', 'Accept': 'application/json'})
                with urlopen(req, timeout=12) as response:
                    data = validate_forecast(json.load(response))
                cached = {'data': data, 'retrieved_at': now, 'site': site,
                          'source': 'Open-Meteo / ECMWF IFS', 'source_url': forecast_url(site)}
                # Store immutable, as-retrieved forecasts for later verification.
                directory = self.root / 'data/products' / 'forecasts'
                directory.mkdir(parents=True, exist_ok=True)
                (directory / f'{now}_{site}.json').write_text(json.dumps(cached, allow_nan=False), encoding='utf-8')
                self.cache[site] = cached
            return {**cached, 'computed_at': now,
                    'windows': [accumulation(cached['data'], now, h) for h in (5, 12)],
                    'model_initialization_time': None,
                    'note': 'Retrieval time is not model initialization. Edge hours assume uniform rainfall.'}
