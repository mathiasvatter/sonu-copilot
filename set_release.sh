#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$ROOT_DIR/VERSION"
CHANGELOG_FILE="$ROOT_DIR/CHANGELOG.md"
DIST_DIR="$ROOT_DIR/dist"
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
ASSET_PATH="$ROOT_DIR/${TAG}-sonu-copilot.zip"

# Reading the changelog content
if [ -f "$CHANGELOG_FILE" ]; then
	BODY=$(<"$CHANGELOG_FILE")
else
	echo "Error: CHANGELOG.md file not found." >&2
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

# 7) Neuen Tag setzen und pushen
git tag "$TAG"
git push origin "$TAG"

# Dist artifacts zippen (für GitHub Release Asset)
rm -f "$ASSET_PATH"
(cd "$DIST_DIR" && zip -r "$ASSET_PATH" .)

# Create the release
gh release create "$TAG" \
  --repo "$REPO" \
  --title "$TITLE" \
  --notes "$BODY" \
  "$ASSET_PATH"
#   --draft \

echo "Release ready: $TAG"
