# dlpTube

A lightweight Linux desktop viewer for local yt-dlp video archives.

## Features

- Original playlist order and shuffled thumbnail grid
- Integrated video player with fullscreen support
- Automatic thumbnail generation
- Original video descriptions
- Fully offline, with no modifications to your archive

## Installation

Download the AppImage from Releases, make it executable and run it.

FFmpeg is required for generating missing thumbnails.

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## License

[MIT](LICENSE)
