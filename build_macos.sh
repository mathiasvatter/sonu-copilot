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
# Ship a consistent unsigned/ad-hoc signed bundle:
# 1) drop stale signature metadata
# 2) clear extended attrs in the bundle
# 3) apply ad-hoc signature so internals are coherent
codesign --remove-signature "$APP_PATH" >/dev/null 2>&1 || true
xattr -cr "$APP_PATH" >/dev/null 2>&1 || true
codesign --force --deep --sign - "$APP_PATH"

MACOS_README_PATH="dist/README-macOS.txt"
cat > "$MACOS_README_PATH" <<EOF
Sonu Co-Pilot (macOS) - Install / First Start
=============================================

Why this warning appears:
- This app is currently not signed/notarized with an Apple Developer ID.
- macOS may block first launch with a security warning.

How to open the app:
1) Move "Sonu Co-Pilot.app" to Applications (recommended).
2) Try to open the app once (it may be blocked).
3) Open System Settings -> Privacy & Security.
4) Scroll to Security section and click "Open Anyway" for Sonu Co-Pilot.
5) Confirm with "Open".

If needed (Terminal fallback):
- Remove quarantine attribute:
  xattr -d com.apple.quarantine "<path/to/Sonu Co-Pilot.app>"

Note:
- You may need to repeat "Open Anyway" after each new downloaded version.
EOF

rm -rf "build" "${APP_NAME}.spec"
rm -rf "dist/${APP_NAME}"

echo "Build complete: dist/${APP_NAME}.app"
