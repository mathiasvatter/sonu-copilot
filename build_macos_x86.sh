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

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: This script is intended for macOS."
  exit 1
fi

if ! command -v arch >/dev/null 2>&1; then
  echo "Error: 'arch' command not found."
  exit 1
fi

if ! arch -x86_64 /usr/bin/true >/dev/null 2>&1; then
  cat <<'EOF'
Error: Rosetta 2 is not available on this machine.
Install it with:
  softwareupdate --install-rosetta --agree-to-license
EOF
  exit 1
fi

# Apple Silicon workflow:
# 1) Use an x86_64 base Python (usually Intel Homebrew in /usr/local/bin/python3).
# 2) Create/use a dedicated x86 virtualenv.
# 3) Run pip + PyInstaller through Rosetta.
VENV_DIR="${VENV_DIR:-venv_x86}"
PYTHON_X86="${PYTHON_X86:-}"

is_x86_python() {
  local py="$1"
  [[ -x "$py" ]] || return 1
  arch -x86_64 "$py" -c 'import platform; assert platform.machine()=="x86_64"' >/dev/null 2>&1
}

choose_base_python() {
  if [[ -n "$PYTHON_X86" ]] && is_x86_python "$PYTHON_X86"; then
    echo "$PYTHON_X86"
    return 0
  fi

  local candidates=(
    "/usr/local/bin/python3"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3.11"
    "/usr/local/bin/python3.10"
  )

  local py
  for py in "${candidates[@]}"; do
    if is_x86_python "$py"; then
      echo "$py"
      return 0
    fi
  done

  return 1
}

if [[ ! -x "${VENV_DIR}/bin/python3" ]]; then
  BASE_PYTHON="$(choose_base_python || true)"
  if [[ -z "${BASE_PYTHON:-}" ]]; then
    cat <<'EOF'
Error: No usable x86_64 Python found for Apple Silicon.
Expected one of:
  - PYTHON_X86=/path/to/x86_64/python3
  - Intel Homebrew Python at /usr/local/bin/python3

Tip (install Intel Homebrew Python under Rosetta):
  arch -x86_64 /bin/bash -lc 'brew install python'
Then rerun this script.
EOF
    exit 1
  fi

  echo "Creating ${VENV_DIR} with x86_64 Python: ${BASE_PYTHON}"
  arch -x86_64 "$BASE_PYTHON" -m venv "$VENV_DIR"
fi

PYTHON_BIN="${VENV_DIR}/bin/python3"
if ! is_x86_python "$PYTHON_BIN"; then
  echo "Error: ${PYTHON_BIN} is not runnable as x86_64. Remove ${VENV_DIR} and recreate with an Intel Python."
  exit 1
fi

arch -x86_64 "$PYTHON_BIN" -m pip install --upgrade pip pyinstaller
if [[ -f "requirements.txt" ]]; then
  arch -x86_64 "$PYTHON_BIN" -m pip install -r requirements.txt
fi

arch -x86_64 "$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --target-arch x86_64 \
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

echo "x86_64 build complete on Apple Silicon: dist/${APP_NAME}.app"
