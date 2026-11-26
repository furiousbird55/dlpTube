# dlpTube

A tiny offline Linux desktop viewer for your existing yt-dlp archive. Browse in original playlist order or a shuffled thumbnail grid, click a video and watch it. No account, server, database or downloader.

## Features

- Two views: ordered playlist and randomized grid.
- Local MKV, MP4 and WebM playback (codec support depends on Qt's backend).
- Play/pause, seeking, volume, video-only fullscreen and original descriptions.
- Existing local thumbnails or cached FFmpeg-generated previews.
- External drive support; the application does not intentionally write to the archive.

## Run from source

Python 3.10 or later, a Linux desktop and optional system FFmpeg for missing thumbnails.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

For previews, install `ffmpeg` through your distribution's package manager if it is not already installed. Select your archive folder. dlpTube recursively matches `name.info.json` to `name.mkv` (or another supported extension). Existing image sidecars are used when readable; otherwise previews are generated locally. Playlist `entries` IDs take priority over `playlist_index`; unranked videos are appended in filename order. Multiple playlist files are combined in path order, not presented as separate playlists. Missing media are skipped. Keep the drive mounted at a consistent path and rescan after reconnecting. Settings and cached thumbnails use Qt's standard user directories. This renamed build is still able to reuse the previous LocalTube folder and volume settings.

Keyboard: **Space** toggles playback, **F** toggles fullscreen, **Escape** exits fullscreen or returns to the library.

## AppImage (experimental build)

The GitHub Actions workflow builds an x86_64 AppImage on Ubuntu 22.04. In your repository, open **Actions → Test and build Linux AppImage → Run workflow**. Download the `dlpTube-linux-x86_64` artifact from the successful run. Extract the artifact ZIP, then:

```sh
sha256sum -c dlpTube-0.3.0-x86_64.AppImage.sha256
chmod +x dlpTube-0.3.0-x86_64.AppImage
./dlpTube-0.3.0-x86_64.AppImage
```

If FUSE is unavailable, try `./dlpTube-0.3.0-x86_64.AppImage --appimage-extract-and-run`.

The bundle is intended to include Python and Qt, but uses system FFmpeg for thumbnail generation. It may still require host graphics/audio libraries. This build has not yet been executed or validated on target distributions. The workflow uploads artifacts, not public releases. Test the binary before attaching it to a release. The checksum checks integrity, not publisher identity. The appimagetool continuous download and action tags are not immutable pins.

To build locally on Linux x86_64, install the dependencies above, download appimagetool from https://github.com/AppImage/appimagetool/releases, and run:

```sh
python -m pip install -r requirements-build.txt
APPIMAGETOOL=/absolute/path/to/appimagetool bash packaging/build-appimage.sh
```

## Status and tests

v0.2 playback and UI were reported working by a prior Linux tester on Linux. v0.3.0 is a release candidate; packaging and updated GUI need real desktop testing. Run `python -m unittest discover -v` (FFmpeg required for the thumbnail integration test). No telemetry or network requests are implemented by dlpTube itself. For stronger archive protection, mount it read-only. See `RELEASE_CHECKLIST.md` before publishing.

## License

Proposed MIT license for original application code; the repository owner must confirm the copyright notice before publishing. Dependencies have separate licenses, including Qt/PySide6 under LGPL/GPL/commercial terms; binary distribution requires a separate dependency-license review.
