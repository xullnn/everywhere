# Focus and output-mode manual test matrix

Run these on macOS after launching LocalVoiceInput. Test both `--mock-asr` and real FunASR mode.

| # | App / state | Expected mode | Expected output |
|---|---|---|---|
| 1 | Apple Notes text area focused | Cursor Mode | Auto-paste. If AX verification confirms insertion, original clipboard is restored; otherwise text remains on clipboard. |
| 2 | Safari page body, no input focused | Clipboard Draft Mode | Result stays on clipboard; no automatic paste. |
| 3 | Chrome ChatGPT input focused | Cursor Mode | Auto-paste or copy fallback if paste cannot be verified. |
| 4 | Chrome page body, no input focused | Clipboard Draft Mode | Copy only. |
| 5 | WeChat chat input focused | Cursor Mode | Auto-paste; do not auto-send. |
| 6 | Slack message box focused | Cursor Mode | Auto-paste or safe copy fallback. |
| 7 | Cursor editor focused | Cursor Mode | Auto-paste or safe copy fallback. |
| 8 | VS Code editor focused | Cursor Mode | Auto-paste or safe copy fallback. |
| 9 | Finder file rename field focused | Cursor Mode | Auto-paste or safe copy fallback. |
| 10 | Password field focused | Clipboard Draft Mode | Never auto-paste. |
| 11 | Start in input field, switch app while recording | Clipboard Draft Mode | Downgrade to copy. |
| 12 | Accessibility/Input Monitoring permission missing | Fallback behavior | Hotkey may fail with permission message; menu mock test should still show copy behavior. |
| 13 | Long draft mode via Option+Space | Floating Draft Mode | Copy + save history. |
| 14 | Press Esc while recording | Cancelled | No copy, no paste. |
| 15 | Paste target rejects Cmd+V | Fallback Copy Mode | Result remains on clipboard. |
| 16 | Original clipboard contains multiple copied items/files | Cursor Mode | After confirmed paste, original clipboard should restore item grouping. |
| 17 | FunASR emits offline segment while still holding shortcut | Recording continues | Do not paste/copy until shortcut is released. |
| 18 | ASR connection fails after partial text | Fallback Copy Mode | Latest partial text is copied instead of leaving session stuck. |
