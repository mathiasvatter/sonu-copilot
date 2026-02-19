#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

APP_NAME="Sonu Co-Pilot"
ENTRY_POINT="main.py"
ICON_PATH="icons/icon.icns"
APP_VERSION="0.0.1"

if [[ -f "venv/bin/activate" ]]; then
  # Use local virtualenv if present.
  source "venv/bin/activate"
fi

python3 -m pip install --upgrade pyinstaller

pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ICON_PATH" \
  --add-data "icons:icons" \
  --add-data "theme:theme" \
  --paths "$ROOT_DIR" \
  "$ENTRY_POINT"

INFO_PLIST="dist/${APP_NAME}.app/Contents/Info.plist"
if [[ -f "$INFO_PLIST" ]]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $APP_VERSION" "$INFO_PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $APP_VERSION" "$INFO_PLIST"
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $APP_VERSION" "$INFO_PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $APP_VERSION" "$INFO_PLIST"
fi

rm -rf "build" "${APP_NAME}.spec"
rm -rf "dist/${APP_NAME}"

echo "Build complete: dist/${APP_NAME}.app"
