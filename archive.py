"""Read-only yt-dlp archive discovery (standard library only)."""
from dataclasses import dataclass
from pathlib import Path
import json
import math

VIDEO_EXTS = ('.mkv', '.mp4', '.webm', '.mov', '.avi', '.m4v')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.avif')

@dataclass(frozen=True)
class Video:
    path: Path
    title: str
    channel: str
    thumbnail: Path | None
    duration: float
    video_id: str
    index: int | None
    description: str = ""


def scan(root: Path):
    if not root.is_dir():
        raise OSError(f'Archive unavailable: {root}')
    videos, playlists, warnings = [], [], []
    for p in sorted(root.rglob('*.info.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(d, dict):
                raise ValueError('Expected JSON object')
            if d.get('_type') in ('playlist', 'multi_video') or isinstance(d.get('entries'), list):
                playlists.append((p, d))
                continue
            stem = str(p)[:-len('.info.json')]
            media = next((Path(stem + ext) for ext in VIDEO_EXTS if Path(stem + ext).is_file()), None)
            if media is None:
                continue
            thumb = next((Path(stem + ext) for ext in IMAGE_EXTS if Path(stem + ext).is_file()), None)
            try:
                index = int(d['playlist_index'])
            except (KeyError, TypeError, ValueError, OverflowError):
                index = None
            try:
                duration = float(d.get('duration') or 0)
                if not math.isfinite(duration) or duration < 0:
                    duration = 0
            except (TypeError, ValueError):
                duration = 0
            description = str(d.get('description') or '')
            sidecar = Path(stem + '.description')
            if sidecar.is_file():
                try:
                    description = sidecar.read_text(encoding='utf-8', errors='replace') or description
                except OSError:
                    pass
            videos.append(Video(media, str(d.get('title') or media.stem), str(d.get('channel') or d.get('uploader') or ''), thumb, duration, str(d.get('id') or ''), index, description))
        except (OSError, ValueError, TypeError) as e:
            warnings.append(f'{p.name}: {e}')
    # Combine explicit playlist orders in path order; append remaining videos.
    ranks = {}
    for _, playlist in playlists:
        entries = playlist.get('entries')
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get('id'):
                ranks.setdefault(str(entry['id']), len(ranks))
    videos.sort(key=lambda v: (0, ranks[v.video_id]) if v.video_id in ranks else (1, v.index) if v.index is not None else (2, v.path.name.casefold()))
    return videos, warnings
