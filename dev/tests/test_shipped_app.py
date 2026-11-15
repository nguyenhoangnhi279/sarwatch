"""Actual shipped case through the real HTTP handler, using in-memory connections.

No claim of browser rendering or live-socket connectivity is made here.
"""
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from app.server.web_server import AnalysisStore, make_handler

ROOT=Path(__file__).resolve().parents[2]


class Assets(HTMLParser):
    def __init__(self):super().__init__();self.paths=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        value=attrs.get('src') if tag=='script' else attrs.get('href') if tag=='link' else None
        if value and value.startswith('./'):self.paths.append('/'+value[2:])


class ShippedApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handler=make_handler(AnalysisStore(ROOT),ROOT/'app/web',weather=SimpleNamespace(current=lambda site:None))

    def get(self,path):
        request=f'GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'.encode()
        class Connection:
            def __init__(self):self.output=bytearray()
            def makefile(self,*args):return io.BytesIO(request)
            def sendall(self,data):self.output.extend(data)
        connection=Connection()
        self.handler(connection,('127.0.0.1',12345),SimpleNamespace(server_name='localhost',server_port=8000))
        header,_,body=bytes(connection.output).partition(b'\r\n\r\n')
        self.assertEqual(int(header.split(b' ',2)[1]),200,path)
        return body

    def test_every_static_entry_asset_and_real_case_load(self):
        parser=Assets();parser.feed(self.get('/').decode('utf-8'))
        self.assertGreater(len(parser.paths),10)
        for path in parser.paths:self.assertGreater(len(self.get(path)),0,path)
        for number in range(4):self.assertGreater(len(self.get(f'/fonts/be-vietnam-{number}.ttf')),1000)
        analysis=json.loads(self.get('/api/analysis'))
        self.assertEqual(len(analysis['geojson']['features']),1646)
        self.assertAlmostEqual(analysis['manifest']['screened_area_km2'],9.3045)
        for date in ['before','after']:self.assertTrue(self.get('/api/preview/'+date+'.png').startswith(b'\x89PNG'))

    def test_download_report_has_exposure_and_optical_evidence(self):
        report=json.loads(self.get('/api/download/report.json'))
        self.assertIn('impact',report)
        self.assertIn('optical_crosscheck',report)
        self.assertEqual(report['status'],'unvalidated')
        self.assertEqual(report['impact']['summary']['candidate_count'],1646)


if __name__=='__main__':unittest.main()
