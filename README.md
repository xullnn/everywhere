# LocalVoiceInput MVP

LocalVoiceInput is a local-first macOS voice input assistant designed around the product shape discussed in the planning conversation:

- Press and hold **Right Option** to dictate.
- A non-focus-stealing floating panel shows realtime transcription.
- If an editable input field is focused, the final text is pasted automatically.
- If no input field is focused, the final text is copied to the clipboard.
- If paste is unsafe or fails, the final text remains on the clipboard.
- Auto-paste restores the previous clipboard; clipboard-draft mode intentionally keeps the dictated text on the clipboard.
- `Option + Space` starts/stops long draft mode.
- `Esc` cancels the current session.

This package contains the Swift Package source, macOS app implementation, FunASR WebSocket integration, mock ASR mode, correction pipeline, history store, and unit tests for the core logic.

## Important limitation

The app must be validated on a real Mac because the product relies on macOS Accessibility, Input Monitoring, Microphone, pasteboard, and global event-tap behavior. The current local build has been validated with full Xcode selected and the Swift test suite runs 45 unit tests.

## Requirements

Recommended:

- macOS 13 or later
- Apple Silicon Mac, tested target: MacBook Pro M4 / 48GB
- Full Xcode selected with `xcode-select`
- Python 3.10 or 3.11 for the optional FunASR local server

## Quick start: mock ASR mode

Mock mode lets you verify the app shell, shortcuts, focus detection, floating panel, clipboard, and paste behavior without running FunASR.

```bash
cd LocalVoiceInput
bash scripts/write_default_config.sh
swift run LocalVoiceInputMac --mock-asr
```

After launch:

1. Grant microphone and accessibility permissions if prompted.
2. Put the cursor in a text field and hold **Right Option**.
3. Release **Right Option**.
4. The mock transcript should be pasted into the focused input field.
5. Click a webpage body or non-input region and repeat; this time the result should be copied to the clipboard instead.

You can also launch a mock session from the menu bar item.

## Build a `.app` bundle on macOS

```bash
cd LocalVoiceInput
bash scripts/build_macos_app.sh
open dist/LocalVoiceInput.app
```

The build script uses `LOCALVOICEINPUT_CODESIGN_IDENTITY` when set. If exactly one valid code-signing identity exists, it uses that identity automatically; otherwise it falls back to ad-hoc signing. For regular testing, prefer a stable Apple Development or local code-signing certificate so macOS TCC permissions survive rebuilds.

macOS may require you to approve the app under:

- System Settings → Privacy & Security → Accessibility
- System Settings → Privacy & Security → Input Monitoring
- System Settings → Privacy & Security → Microphone

## Real ASR mode with FunASR

First install the local FunASR runtime:

```bash
cd LocalVoiceInput
bash scripts/setup_funasr_venv.sh
```

Download the local smoke-test models:

```bash
bash scripts/download_funasr_smoke_models.sh
```

Then start the local WebSocket server in a terminal that will remain open:

```bash
bash scripts/run_funasr_python_server.sh
```

Optional server smoke test:

```bash
bash scripts/smoke_test_funasr_server.sh
```

In another terminal, run the app or open the packaged app:

```bash
swift run LocalVoiceInputMac --asr-url ws://127.0.0.1:10095
# or
bash scripts/write_default_config.sh
open dist/LocalVoiceInput.app
```

The first FunASR setup downloads models. After the models are cached locally, the ASR runtime can be used offline. The server defaults to CPU and uses cached local model paths when present. Punctuation and speaker verification are disabled by default for smoke testing; enable them explicitly with `FUNASR_PUNC_MODEL` or `FUNASR_SV_MODEL` if needed.

## Configuration

The app reads config from:

```text
~/Library/Application Support/LocalVoiceInput/config.json
```

Create a default config:

```bash
bash scripts/write_default_config.sh
```

Example config is also available at:

```text
configs/config.example.json
```

Important options:

```json
{
  "asrURL": "ws://127.0.0.1:10095",
  "mockASR": false,
  "hotwords": {
    "qwen三": "Qwen3",
    "fun asr": "FunASR"
  },
  "homophones": {
    "玄界芯片": "玄戒芯片"
  },
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
```

## Architecture

```text
macOS menu bar app
  -> HotkeyController
  -> FocusDetector
  -> OutputModeRouter
  -> FloatingPanelController
  -> AudioCapture
  -> ASRClientProtocol
      -> FunASRClient / MockASRClient
  -> TranscriptBuffer
  -> CorrectionPipeline
  -> PasteEngine
      -> ClipboardManager
      -> KeyboardSimulator
  -> HistoryStore
```

### Output rules

| Situation | Output mode | Clipboard behavior |
|---|---|---|
| Editable text field focused | Cursor Mode | Temporarily write result, Cmd+V, restore original clipboard |
| No input focused | Clipboard Draft Mode | Keep result on clipboard |
| Secure text field | Clipboard Draft Mode | Never auto-paste |
| Focus changes while recording | Clipboard Draft Mode | Downgrade to copy |
| Paste uncertain/fails | Fallback Copy Mode | Keep result on clipboard |
| Long draft mode | Floating Draft Mode | Copy + save history |
| Esc cancel | Cancelled | No copy, no paste |

## Testing

Run core tests:

```bash
bash scripts/test.sh
```

Current automated coverage includes:

- output mode routing
- secure-field protection
- no-focus clipboard draft mode
- focus-change downgrade
- transcript partial/final merging
- session-id isolation for stale ASR events
- late partial protection
- hotword correction
- homophone correction
- punctuation normalization
- history retention
- session state machine

Manual macOS test matrices are in:

```text
eval/focus_cases.md
eval/asr_cases.md
```

## Known MVP limitations

- It is not yet an InputMethodKit input method, so realtime partial text appears in the floating panel, not directly inside the target input field.
- Right Option detection uses a global event tap. Some keyboard layouts, remapped keys, or permission states may require changing the shortcut implementation.
- Paste success detection is intentionally conservative. The app restores the previous clipboard only when Accessibility verification can confirm that the target text changed; otherwise it keeps the dictated text on the clipboard to avoid losing content.
- The correction layer is rule-based in this MVP. A local LLM refiner can be added behind `CorrectionPipeline` later.
- The FunASR runtime is local, but first setup still needs to download Python packages and model files. Keep the server running in a user terminal or a LaunchAgent for manual app testing.

## Review fixes included in this build

This reviewed build fixes several MVP-level issues found during a full implementation pass:

- FunASR offline segment results no longer prematurely finish a session while the user is still holding the shortcut.
- Pending audio is flushed before sending `is_speaking=false`, reducing the chance of losing the final chunk.
- Clipboard restoration is safer: previous clipboard content is restored only after paste verification; otherwise the dictated text remains available for manual `⌘V`.
- Clipboard snapshots now preserve multiple pasteboard items instead of flattening all types into one item.
- Stale ASR events from old sessions are ignored.
- Right Option push-to-talk is debounced so `Option + Space` can be used for long draft mode without accidentally starting a push-to-talk session.
- ASR/runtime errors attempt to salvage the latest partial transcript into clipboard fallback mode instead of leaving the app stuck in an active session.

## Suggested next steps

1. Build and run mock mode on the target Mac.
2. Validate focus and clipboard behavior using `eval/focus_cases.md`.
3. Run FunASR locally and validate ASR quality using `eval/asr_cases.md`.
4. Add Qwen3-ASR/MLX as an optional final refiner if FunASR quality is not enough for your Chinese dictation workload.
5. Build a future InputMethodKit version for true in-field realtime preedit.
