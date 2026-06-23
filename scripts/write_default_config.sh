#!/usr/bin/env bash
set -euo pipefail
CONFIG_DIR="$HOME/Library/Application Support/LocalVoiceInput"
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/config.json" <<'JSON'
{
  "asrURL": "ws://127.0.0.1:10095",
  "mockASR": false,
  "mockTranscript": "这是一次本地语音输入测试，松开快捷键以后会自动粘贴或者复制到剪切板。",
  "hotwords": {
    "qwen三": "Qwen3",
    "fun asr": "FunASR",
    "麦克布克 pro": "MacBook Pro"
  },
  "homophones": {},
  "outputPolicy": {
    "autoPasteEnabled": true,
    "restoreClipboardAfterPaste": true,
    "downgradeToClipboardWhenFocusChanges": true,
    "pasteSecureFields": false,
    "preferClipboardForLowConfidence": true
  },
  "correctionMode": "clean",
  "historyMaxItems": 20
}
JSON
echo "Wrote $CONFIG_DIR/config.json"
