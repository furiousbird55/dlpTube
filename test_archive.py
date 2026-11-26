import json
import tempfile
import unittest
from pathlib import Path
from archive import scan

class ArchiveTest(unittest.TestCase):
    def test_order_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, index in [('a', 2), ('b', 1)]:
                (root / f'{name}.mkv').touch()
                (root / f'{name}.info.json').write_text(json.dumps({'id': name, 'title': name, 'playlist_index': index}))
            (root / 'a.webp').touch()
            (root / 'playlist.info.json').write_text(json.dumps({'_type':'playlist', 'entries':[{'id':'a'}, {'id':'missing'}, {'id':'b'}]}))
            before = {p.name:p.read_bytes() for p in root.iterdir()}
            videos, warnings = scan(root)
            self.assertEqual([v.video_id for v in videos], ['a','b'])
            self.assertEqual(videos[0].thumbnail, root/'a.webp')
            self.assertFalse(warnings)
            self.assertEqual(before, {p.name:p.read_bytes() for p in root.iterdir()})
            (root/'playlist.info.json').unlink()
            self.assertEqual([v.video_id for v in scan(root)[0]], ['b','a'])
    def test_missing_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError): scan(Path(tmp)/'missing')
    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'bad.info.json').write_text('{')
            self.assertEqual(len(scan(Path(tmp))[1]), 1)

    def test_invalid_duration_and_playlist_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'a.mkv').touch()
            (root/'a.info.json').write_text(json.dumps({'id':'a','duration':'Infinity'}))
            (root/'playlist.info.json').write_text(json.dumps({'_type':'playlist','entries':42}))
            videos, warnings = scan(root)
            self.assertEqual(videos[0].duration, 0)
            self.assertFalse(warnings)

    def test_description_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'a.mkv').touch()
            (root/'a.info.json').write_text(json.dumps({'description':'json'}))
            (root/'a.description').write_text('sidecar')
            self.assertEqual(scan(root)[0][0].description, 'sidecar')

if __name__ == '__main__': unittest.main()
