#!/usr/bin/env bash
set -euo pipefail

chmod +x linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-plugin-appimage-x86_64.AppImage

export ARCH=x86_64
export OUTPUT=appimage

./linuxdeploy-x86_64.AppImage \
  --appdir AppDir \
  --desktop-file AppDir/gsm.desktop \
  --icon-file AppDir/gsm.png \
  --output appimage
