#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
APP_NAME="LocalVoiceInput"
PRODUCT="LocalVoiceInputMac"
BUNDLE_ID="dev.localvoiceinput.mvp"
DIST_DIR="$PWD/dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

swift build -c release --product "$PRODUCT"
rm -rf "$APP_DIR"
mkdir -p "$MACOS" "$RESOURCES"
cp ".build/release/$PRODUCT" "$MACOS/$APP_NAME"

cat > "$CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key><string>en</string>
  <key>CFBundleExecutable</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>LocalVoiceInput uses the microphone to transcribe your speech locally.</string>
  <key>NSAppleEventsUsageDescription</key><string>LocalVoiceInput may simulate paste actions into the frontmost app.</string>
  <key>NSInputMonitoringUsageDescription</key><string>LocalVoiceInput uses global keyboard shortcuts for push-to-talk and cancellation.</string>
</dict>
</plist>
PLIST

if command -v codesign >/dev/null 2>&1; then
  SIGN_IDENTITY="${LOCALVOICEINPUT_CODESIGN_IDENTITY:-}"
  if [[ -z "$SIGN_IDENTITY" ]] && command -v security >/dev/null 2>&1; then
    IDENTITIES_TEXT="$(security find-identity -p codesigning -v | sed -n 's/.*"\(.*\)".*/\1/p')"
    IDENTITY_COUNT="$(printf '%s\n' "$IDENTITIES_TEXT" | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "$IDENTITY_COUNT" == "1" ]]; then
      SIGN_IDENTITY="$IDENTITIES_TEXT"
    fi
  fi

  if [[ -n "$SIGN_IDENTITY" ]]; then
    echo "Signing with identity: $SIGN_IDENTITY"
    codesign --force --deep --sign "$SIGN_IDENTITY" "$APP_DIR"
  else
    echo "Signing ad-hoc. Set LOCALVOICEINPUT_CODESIGN_IDENTITY to keep TCC permissions stable across rebuilds."
    codesign --force --deep --sign - "$APP_DIR" >/dev/null 2>&1 || true
  fi
fi

echo "Built: $APP_DIR"
echo "Open it with: open '$APP_DIR'"
if command -v codesign >/dev/null 2>&1; then
  codesign -dr - "$APP_DIR" 2>&1 || true
fi
