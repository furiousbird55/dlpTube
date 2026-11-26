"""Generate local thumbnails without modifying the archive."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def thumbnail(video, cache, ffmpeg=None):
    if video.thumbnail and video.thumbnail.is_file():
        return video.thumbnail
    ffmpeg = ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:
        return None
    try:
        stat = video.path.stat()
        key = hashlib.sha256(f'{video.path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()
        cache = Path(cache)
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / (key + '.jpg')
        if target.is_file() and target.stat().st_size:
            return target
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            frame = Path(tmp) / 'frame.jpg'
            for timestamp in (min(30, video.duration * .15), 0):
                result = subprocess.run([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(timestamp), '-i', str(video.path), '-map', '0:v:0', '-frames:v', '1', '-vf', 'scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2', str(frame)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                if result.returncode == 0 and frame.is_file() and frame.stat().st_size:
                    os.replace(frame, target)
                    return target
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None
