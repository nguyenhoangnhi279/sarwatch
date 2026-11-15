"""Checksums survive Git newline conversion without hiding content changes."""
from pathlib import Path
import tempfile
import unittest

from dev.build.verify_repository import fingerprint


class RepositoryChecksumTests(unittest.TestCase):
    def test_text_newlines_and_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ['.json','.js','.osm','.txt']:
                with self.subTest(suffix=suffix):
                    path=Path(directory)/('metadata'+suffix)
                    path.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')
                    expected=fingerprint(path,'lf')
                    path.write_bytes(b'{\n  "value": 1\n}\n')
                    self.assertEqual(fingerprint(path,'lf'),expected)
                    path.write_bytes(b'{\n  "value": 2\n}\n')
                    self.assertNotEqual(fingerprint(path,'lf'),expected)

    def test_binary_remains_byte_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'radar.tif'
            path.write_bytes(b'\x00\r\n\xff')
            expected=fingerprint(path)
            path.write_bytes(b'\x00\n\xff')
            self.assertNotEqual(fingerprint(path),expected)
            with self.assertRaises(ValueError):
                fingerprint(path,'lf')
