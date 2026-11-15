"""Local, dependency-free HTTP service for SARWatch's browser frontend."""
import csv
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import threading
from urllib.parse import urlsplit, parse_qs
import zipfile

from .data_loader import load_bundle
from .weather import WeatherStore

MAX_UPLOAD = 60_000_000
TABLES = (
    'candidate_screening_summary.csv',
    'terrain_threshold_sensitivity.csv',
    'candidate_threshold_sensitivity.csv',
)


class AnalysisStore:
    def __init__(self, project_root):
        self.root = Path(project_root)
        self.path = self.root / 'data/products' / 'sarwatch_demo_bundle.zip'
        self.lock = threading.RLock()
        self.signature = None
        self.cache = None

    def current(self):
        with self.lock:
            if not self.path.exists():
                return None
            stat = self.path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            if self.signature != signature:
                payload = self.path.read_bytes()
                meta, geo, images, tables = load_bundle(payload)
                csv_tables = {}
                for name in TABLES:
                    if name in tables:
                        csv_tables[name] = list(csv.DictReader(io.StringIO(tables[name].decode('utf-8-sig'))))
                self.cache = {
                    'manifest': meta, 'geojson': geo, 'images': images,
                    'tables': csv_tables, 'raw_tables': tables,
                    'version': hashlib.sha256(payload).hexdigest()[:16],
                }
                self.signature = signature
            return self.cache

    def install(self, payload):
        # Validate before changing the file currently used by the application.
        load_bundle(payload)
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.incoming.zip')
            temporary.write_bytes(payload)
            if self.path.exists():
                shutil.copy2(self.path, self.path.with_name('sarwatch_demo_bundle.previous.zip'))
            temporary.replace(self.path)
            self.signature = None
            return self.current()


def make_handler(store, web_root, weather=None):
    weather = weather or WeatherStore(store.root)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_root), **kwargs)

        def log_message(self, format, *args):
            # Avoid noisy request logs and never log upload contents.
            pass

        def send_bytes(self, content, content_type, status=200, filename=None):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)

        def send_json(self, content, status=200):
            self.send_bytes(json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8'), 'application/json; charset=utf-8', status)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path.startswith('/api/'):
                if path == '/api/verification':
                    report = store.root / 'data/products' / 'verification' / 'rainfall_metrics.json'
                    try:
                        return self.send_json(json.loads(report.read_text(encoding='utf-8')) if report.exists() else {'status': 'not_evaluated'})
                    except (ValueError, OSError):
                        return self.send_json({'status': 'unavailable'}, 503)
                if path == '/api/weather':
                    try:
                        site = parse_qs(urlsplit(self.path).query).get('site', ['hue'])[0]
                        return self.send_json(weather.current(site))
                    except (ValueError, KeyError, TypeError, OSError) as error:
                        return self.send_json({'error': 'Không lấy được dự báo mới. Không suy ra an toàn khi thiếu dữ liệu.', 'detail': type(error).__name__}, 503)
                try:
                    analysis = store.current()
                    if path == '/api/status':
                        return self.send_json({'available': analysis is not None})
                    if analysis is None:
                        return self.send_json({'error': 'Chưa có gói dữ liệu. Hãy nhập ZIP xuất từ Colab.'}, 404)
                    if path == '/api/analysis':
                        return self.send_json({key: analysis[key] for key in ['manifest', 'geojson', 'tables', 'version']})
                    if path in ['/api/preview/before.png', '/api/preview/after.png']:
                        date = path.rsplit('/', 1)[-1].split('.')[0]
                        return self.send_bytes(analysis['images'][date], 'image/png')
                    if path == '/api/download/candidates.geojson':
                        return self.send_bytes(json.dumps(analysis['geojson']).encode(), 'application/geo+json', filename='sarwatch_candidates_unvalidated.geojson')
                    if path == '/api/download/report.json':
                        report = {'manifest': analysis['manifest'], 'tables': analysis['tables'], 'status': 'unvalidated'}
                        impact_path = store.root / 'data/products' / 'impact' / 'review_analysis.json'
                        if impact_path.exists():
                            impact = json.loads(impact_path.read_text(encoding='utf-8'))
                            if impact.get('analysis_version') == analysis['version']:
                                report['impact'] = {key:impact[key] for key in ['summary','sources','ordering','limitations']}
                        reference_path=store.root/'data/products'/'validation'/'optical_crosscheck.json'
                        if reference_path.exists():
                            reference=json.loads(reference_path.read_text(encoding='utf-8'))
                            if reference.get('analysis_version')==analysis['version']:
                                report['optical_crosscheck']={key:reference[key] for key in ['summary','sources','protocol','limitations']}
                        return self.send_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8'), 'application/json', filename='sarwatch_analysis_report.json')
                    if path == '/api/download/bundle.zip':
                        return self.send_bytes(store.path.read_bytes(), 'application/zip', filename='sarwatch_demo_bundle.zip')
                    return self.send_json({'error': 'Không tìm thấy tài nguyên.'}, 404)
                except (ValueError, KeyError, TypeError, OSError, RuntimeError, zipfile.BadZipFile) as error:
                    return self.send_json({'error': 'Gói dữ liệu chưa đọc được: ' + str(error)}, 422)
            # Serve only web assets, never the project root or credentials.
            assets = ['/', '/index.html', '/forecast.css', '/weather-context.css', '/dashboard.css', '/review.css', '/fonts.css', '/forecast.js', '/review.js', '/analysis-data.js', '/impact-data.js', '/styles.css', '/app.js', '/favicon.svg']
            fonts = ['/fonts/be-vietnam-0.ttf', '/fonts/be-vietnam-1.ttf', '/fonts/be-vietnam-2.ttf', '/fonts/be-vietnam-3.ttf', '/fonts/OFL.txt']
            assets += ['/reference-data.js','/reference.js']
            if path not in assets + fonts:
                return self.send_error(404)
            return super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path != '/api/import':
                return self.send_json({'error': 'Không tìm thấy thao tác.'}, 404)
            origin = self.headers.get('Origin')
            if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                return self.send_json({'error': 'Chỉ nhận dữ liệu từ website đang mở trên máy này.'}, 403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_UPLOAD:
                    return self.send_json({'error': 'Chọn một file ZIP không quá 60 MB.'}, 413)
                payload = self.rfile.read(length)
                if len(payload) != length:
                    return self.send_json({'error': 'File tải lên chưa đầy đủ.'}, 400)
                store.install(payload)
                return self.send_json({'ok': True})
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, zipfile.BadZipFile) as error:
                return self.send_json({'error': 'Không thể nhập gói dữ liệu: ' + str(error)}, 422)

    return Handler


def create_server(project_root, port=8000):
    store = AnalysisStore(project_root)
    weather = WeatherStore(project_root)
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(store, Path(project_root) / 'app/web', weather))
    threading.Thread(target=weather.collect_forever, daemon=True).start()
    return server
