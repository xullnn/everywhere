# Output Safety Module

Output safety spans core routing, macOS focus detection, paste execution, clipboard handling, and UI diagnostics.

Stable responsibilities:

- Route to cursor paste only when the initial focus is editable, pasteable, not secure, and sufficiently confident.
- Route to clipboard draft when no text input is focused, the target is secure, confidence is low, auto-paste is disabled, or focus changes during recording.
- Route to fallback copy when paste is attempted but cannot be confirmed.
- Restore the previous clipboard only after paste verification confirms insertion.
- Keep dictated text on the clipboard for no-input, secure-field, focus-change, and paste-failure cases.
- Never copy or paste on Esc cancellation.

Current paste behavior:

- `KeyboardSimulator` posts a clean Right Option key-up before Cmd+V, then posts Cmd+V to the detected target process when available.
- `PasteEngine` verifies insertion using AX text/value/count/range evidence and polls briefly after paste.

Go Deeper:

- See `../../integration/output_safety_flow.md` for detailed routing flow.
