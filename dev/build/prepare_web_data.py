"""Operator command: validate the real Colab export and publish browser assets.

Usage: python -m dev.build.prepare_web_data PATH_TO_EXPORT_ZIP
No user credentials and no raw radar files are copied into the browser bundle.
"""
import argparse
import base64
import json
from pathlib import Path
from app.server.web_server import AnalysisStore


def publish(root, source):
    store = AnalysisStore(root)
    payload = Path(source).read_bytes()
    # install validates polygons, areas, PNGs and bounds before replacing data.
    result = store.install(payload)
    data = {key: result[key] for key in ('manifest', 'geojson', 'tables', 'version')}
    data['imageSources'] = {date: 'data:image/png;base64,' + base64.b64encode(blob).decode('ascii')
                            for date, blob in result['images'].items()}
    script = 'globalThis.SARWatchDataset = ' + json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(',', ':')) + ';\n'
    destination = Path(root) / 'app/web' / 'analysis-data.js'
    destination.write_text(script, encoding='utf-8')
    return {'regions': len(data['geojson']['features']),
            'area_km2': data['manifest']['screened_area_km2'], 'version': data['version']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle')
    args = parser.parse_args()
    print(json.dumps(publish(Path(__file__).resolve().parents[2], args.bundle)))
