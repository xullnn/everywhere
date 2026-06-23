# Review notes for LocalVoiceInput MVP

This review found and fixed several issues that were important for a practical MVP on macOS.

## Fixed issues

1. **FunASR offline segment prematurely ended sessions**
   - Before: any `2pass-offline` event immediately finalized and pasted/copied text.
   - Risk: a pause in the middle of long dictation could end the session early.
   - Fix: offline segment events update the transcript while recording; output routing only happens after the user releases the shortcut or stops long draft mode.

2. **Final audio chunk could be sent after `is_speaking=false`**
   - Before: `finish()` stopped audio asynchronously and sent the final ASR marker immediately.
   - Risk: the last partial chunk could arrive after the server was told the user stopped speaking.
   - Fix: `AudioCapture.stopAndFlush` drains pending PCM chunks first, then `FunASRClient.finish()` sends `is_speaking=false`.

3. **Clipboard restoration was too optimistic**
   - Before: unchanged pasteboard `changeCount` was treated as paste success.
   - Risk: if the target rejected `Cmd+V`, the app restored the old clipboard and the dictated text was lost.
   - Fix: the app restores the previous clipboard only when Accessibility verification can confirm that text was inserted. Otherwise, the dictated text remains on the clipboard.

4. **Clipboard snapshots flattened multiple pasteboard items**
   - Before: all pasteboard item types were restored into one item.
   - Risk: copied files or multi-item clipboard contents could restore incorrectly.
   - Fix: snapshots now preserve item grouping.

5. **Stale ASR events could contaminate a new session**
   - Before: `TranscriptBuffer` accepted events with any session ID.
   - Risk: a late event from a previous websocket or mock timer could appear in a new dictation.
   - Fix: events from different sessions are ignored at both the buffer/app-controller level.

6. **Right Option conflicted with `Option + Space`**
   - Before: pressing Right Option immediately started push-to-talk, so `Option + Space` could not reliably start long draft mode.
   - Fix: Right Option push-to-talk is debounced briefly; `Option + Space` cancels the pending push-to-talk and toggles long draft mode.

7. **ASR errors could leave the app stuck**
   - Before: errors showed a panel message but did not always clear the active session.
   - Risk: the next dictation could be blocked.
   - Fix: errors now clean up the session; if partial text exists, it is copied as fallback.

## Still requiring real Mac validation

The Linux environment can build and test the platform-independent Swift core, but cannot compile or run AppKit, AVFoundation, Accessibility, or event-tap behavior against the macOS SDK. These require validation on the target Mac:

- Right Option event-tap behavior and permissions.
- AVAudioEngine microphone capture and conversion to 16kHz PCM.
- AX focus detection across WeChat, browsers, Cursor, VS Code, Obsidian, Notes, and password fields.
- Paste verification for web editors and Electron apps.
- FunASR server compatibility and latency on Apple Silicon.

## Automated test status

`swift test` currently runs 22 core tests, all passing in this environment. See `test-report.txt`.
