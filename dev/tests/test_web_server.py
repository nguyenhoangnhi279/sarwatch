"""Contract and HTTP tests use isolated synthetic fixtures, not project results."""
import base64
import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from app.server.data_loader import load_bundle
from app.server.web_server import AnalysisStore, make_handler
from types import SimpleNamespace

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


def fixture(overrides=None):
    meta = {'schema_version': 1, 'status': 'test-fixture', 'initial_area_km2': 2, 'screened_area_km2': 1,
            'dates': {'before': '2026-10-15', 'after': '2026-10-27'},
            'previews': {d: {'bounds': [[16.3, 107.4], [16.6, 107.8]]} for d in ['before', 'after']}}
    if overrides:
        meta.update(overrides)
    geo = {'type': 'FeatureCollection', 'features': [{'type': 'Feature',
        'geometry': {'type': 'Polygon', 'coordinates': [[[107.5, 16.4], [107.51, 16.4], [107.51, 16.41], [107.5, 16.4]]]},
        'properties': {'id': 1, 'area_m2': 1000000, 'status': 'test-fixture'}}]}
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(meta))
        z.writestr('screened_candidates.geojson', json.dumps(geo))
        for date in ['before', 'after']:
            z.writestr(date + '_HH.png', PNG)
        z.writestr('candidate_screening_summary.csv', 'group,pixels,area_km2\nTest,10000,1\n')
    return data.getvalue()


class BundleContractTests(unittest.TestCase):
    def test_valid_fixture(self):
        meta, geo, images, tables = load_bundle(fixture())
        self.assertEqual(meta['screened_area_km2'], 1)
        self.assertEqual(len(geo['features']), 1)
        self.assertTrue(images['after'].startswith(b'\x89PNG'))

    def test_area_disagreement(self):
        with self.assertRaisesRegex(ValueError, 'disagree'):
            load_bundle(fixture({'screened_area_km2': 0.5}))

    def test_nonfinite_area(self):
        with self.assertRaisesRegex(ValueError, 'Invalid analysis area'):
            load_bundle(fixture({'screened_area_km2': float('nan')}))

    def test_wrong_coordinate_order(self):
        previews = {d: {'bounds': [[107.4, 16.3], [107.8, 16.6]]} for d in ['before', 'after']}
        with self.assertRaisesRegex(ValueError, 'bounds'):
            load_bundle(fixture({'previews': previews}))


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'app/web').mkdir(parents=True)
        (self.root / 'app/web/index.html').write_text('<!doctype html><title>Test</title>')
        self.handler = make_handler(AnalysisStore(self.root), self.root / 'app/web')
        self.base = 'http://127.0.0.1:8000'

    def tearDown(self):
        self.temp.cleanup()

    def perform(self, method, path, payload=b'', origin=None):
        # Exercise the real HTTP parser/handler using an in-memory connection.
        # This does not claim live socket/browser connectivity was verified.
        headers = ['Host: 127.0.0.1:8000', 'Connection: close']
        if method == 'POST':
            headers += ['Content-Type: application/zip', f'Content-Length: {len(payload)}']
        if origin:
            headers.append('Origin: ' + origin)
        request = (f'{method} {path} HTTP/1.1'+chr(13)+chr(10)+(chr(13)+chr(10)).join(headers)+chr(13)+chr(10)+chr(13)+chr(10)).encode() + payload
        class Connection:
            def __init__(self): self.output = bytearray()
            def makefile(self, *args): return io.BytesIO(request)
            def sendall(self, data): self.output.extend(data)
        connection = Connection()
        self.handler(connection, ('127.0.0.1', 12345), SimpleNamespace(server_name='localhost', server_port=8000))
        header, _, body = bytes(connection.output).partition(b'\r\n\r\n')
        status = int(header.split(b' ', 2)[1])
        if status >= 400:
            raise HTTPError(self.base + path, status, 'HTTP error', None, io.BytesIO(body))
        return status, body

    def get(self, path):
        return self.perform('GET', path)

    def post(self, payload, origin=None):
        return self.perform('POST', '/api/import', payload, origin)

    def test_empty_and_static(self):
        self.assertEqual(self.get('/')[0], 200)
        self.assertFalse(json.loads(self.get('/api/status')[1])['available'])
        with self.assertRaises(HTTPError) as error:
            self.get('/api/analysis')
        self.assertEqual(error.exception.code, 404)
        with self.assertRaises(HTTPError):
            self.get('/README.md')

    def test_import_preview_and_download(self):
        uploaded = fixture()
        self.assertEqual(self.post(uploaded)[0], 200)
        data = json.loads(self.get('/api/analysis')[1])
        self.assertEqual(data['manifest']['screened_area_km2'], 1)
        self.assertEqual(self.get('/api/preview/before.png')[1], PNG)
        geo = json.loads(self.get('/api/download/candidates.geojson')[1])
        self.assertEqual(geo['type'], 'FeatureCollection')
        self.assertEqual(self.get('/api/download/bundle.zip')[1], uploaded)

    def test_invalid_upload_preserves_current(self):
        valid = fixture()
        self.post(valid)
        with self.assertRaises(HTTPError) as error:
            self.post(b'not a ZIP')
        self.assertEqual(error.exception.code, 422)
        self.assertEqual(self.get('/api/download/bundle.zip')[1], valid)
        self.post(valid)
        self.assertEqual((self.root / 'data/products/sarwatch_demo_bundle.previous.zip').read_bytes(), valid)

    def test_cross_origin_import_rejected(self):
        with self.assertRaises(HTTPError) as error:
            self.post(fixture(), origin='https://example.com')
        self.assertEqual(error.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
