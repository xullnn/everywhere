#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

APP_PATH="${1:-dist/LocalVoiceInput.app}"

echo "Available code signing identities:"
security find-identity -p codesigning -v || true
echo

if [[ ! -e "$APP_PATH" ]]; then
  echo "App not found: $APP_PATH" >&2
  exit 1
fi

echo "Code signing details for $APP_PATH:"
codesign -dv "$APP_PATH" 2>&1 || true
echo
echo "Designated requirement:"
codesign -dr - "$APP_PATH" 2>&1 || true
