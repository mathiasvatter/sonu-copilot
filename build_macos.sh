#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

APP_NAME="Sonu Co-Pilot"
ENTRY_POINT="main.py"
ICON_PATH="icons/sonu.icns"
VERSION_FILE="$ROOT_DIR/VERSION"
if [[ ! -f "$VERSION_FILE" ]]; then
  echo "Error: Missing version file at $VERSION_FILE"
  exit 1
fi
APP_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
if [[ -z "$APP_VERSION" ]]; then
  echo "Error: VERSION file is empty"
  exit 1
fi

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

APP_PATH="dist/${APP_NAME}.app"
# Remove any existing signature so we do not ship a bundle with invalid signature metadata.
if codesign -dv "$APP_PATH" >/dev/null 2>&1; then
  codesign --remove-signature "$APP_PATH"
fi

rm -rf "build" "${APP_NAME}.spec"
rm -rf "dist/${APP_NAME}"

echo "Build complete: dist/${APP_NAME}.app"
