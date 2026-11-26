#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${APPIMAGETOOL:?Set APPIMAGETOOL to the absolute path of the official appimagetool executable}"
[[ $(uname -m) == x86_64 ]] || { echo 'This build recipe targets x86_64.' >&2; exit 1; }
python -m unittest discover -v
python -m PyInstaller --noconfirm --clean --onedir --name dlptube --add-data 'packaging/dlptube.svg:packaging' main.py
appdir="$PWD/build/dlpTube.AppDir"
rm -rf "$appdir"
mkdir -p "$appdir/usr/bin"
cp -a dist/dlptube/. "$appdir/usr/bin/"
cp packaging/dlptube.desktop packaging/dlptube.svg "$appdir/"
cp packaging/dlptube.svg "$appdir/.DirIcon"
cat > "$appdir/AppRun" <<'RUN'
#!/bin/sh
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$HERE/usr/bin/dlptube" "$@"
RUN
chmod +x "$appdir/AppRun"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" "$appdir" "$PWD/dist/dlpTube-0.3.0-x86_64.AppImage"
(cd dist && sha256sum dlpTube-0.3.0-x86_64.AppImage > dlpTube-0.3.0-x86_64.AppImage.sha256)
