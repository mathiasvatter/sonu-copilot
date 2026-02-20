#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$ROOT_DIR/VERSION"
CHANGELOG_FILE="$ROOT_DIR/CHANGELOG.md"
RELEASE_ASSETS_DIR="${RELEASE_ASSETS_DIR:-$ROOT_DIR/release-assets}"
REPO="mathiasvatter/sonu-copilot"
DRAFT="false"
PRERELEASE="false"

VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
if [[ -z "$VERSION" ]]; then
  echo "Error: VERSION is empty." >&2
  exit 1
fi
TAG="v${VERSION}"
TITLE="$TAG"

# Reading the changelog content
if [ -f "$CHANGELOG_FILE" ]; then
  BODY=$(<"$CHANGELOG_FILE")
else
  echo "Error: CHANGELOG.md file not found." >&2
  exit 1
fi

if [[ ! -d "$RELEASE_ASSETS_DIR" ]]; then
  echo "Error: release assets dir not found: $RELEASE_ASSETS_DIR" >&2
  exit 1
fi

mapfile -d '' ASSET_FILES < <(find "$RELEASE_ASSETS_DIR" -maxdepth 1 -type f -name '*.zip' -print0 | sort -z)
if [[ ${#ASSET_FILES[@]} -eq 0 ]]; then
  echo "Error: no release assets found in $RELEASE_ASSETS_DIR" >&2
  exit 1
fi

# remove existing tag and GitHub release if they exist
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Lösche lokalen Tag $TAG..."
  git tag -d "$TAG"
  git push --delete origin "$TAG"
fi

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "Lösche GitHub-Release $TAG..."
  gh release delete "$TAG" --repo "$REPO" --yes
fi

# Neuen Tag setzen und pushen
git tag "$TAG"
git push origin "$TAG"

# Create the release with one asset per OS/arch zip
gh release create "$TAG" \
  --repo "$REPO" \
  --title "$TITLE" \
  --notes "$BODY" \
  "${ASSET_FILES[@]}"
#   --draft

echo "Release ready: $TAG"
