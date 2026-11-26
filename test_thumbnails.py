import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from archive import Video
from thumbnails import thumbnail

@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg not installed')
class ThumbnailTest(unittest.TestCase):
    def test_generate_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / 'test.mkv'
            subprocess.run(['ffmpeg','-loglevel','error','-f','lavfi','-i','color=blue:s=160x90:d=1','-c:v','ffv1',str(media)],check=True)
            before = media.read_bytes()
            video = Video(media,'Test','',None,1,'test',None)
            result = thumbnail(video,root/'cache')
            self.assertTrue(result.is_file())
            self.assertEqual(result, thumbnail(video,root/'cache'))
            self.assertEqual(before,media.read_bytes())
