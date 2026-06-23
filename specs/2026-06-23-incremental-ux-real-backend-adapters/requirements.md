# Requirements - Incremental UX Real Backend Adapters

## Problem

`incremental_ux_gate.py` is the canonical gate for LocalVoiceInput perceived-realtime backend readiness, but it currently accepts only fake in-process adapters. That blocks real model comparison because Qwen3, MiMo, FunASR, or future services cannot be tested through the same timed PCM, partial/final, stale-session, and cancellation gate.

## Scope

### IN

- Add a real localhost transport adapter to `eval/asr_streaming/incremental_ux_gate.py`.
- Keep the adapter backend-neutral so later Qwen3, MiMo, FunASR, or other local services can implement the same protocol.
- Preserve existing fake adapters and self-tests.
- Add a controlled local fake HTTP service for validation so the gate can prove real transport behavior without loading a large ASR model.
- Record per-case event and chunk artifacts in the existing gate format.
- Keep all work local/offline and isolated to eval/spec/script files.

### OUT

- No Swift App runtime integration.
- No macOS hotkey, focus, paste, clipboard, or floating-panel changes.
- No cloud ASR or remote inference.
- No InputMethodKit work.
- No Qwen3/MiMo/FunASR model service implementation in this feature.
- No final backend role decision in this feature.

## Requirements

- R1: `incremental_ux_gate.py` must expose at least one real transport adapter, initially `http-json`, that sends start/chunk/finish/cancel requests to a localhost service.
- R2: The transport protocol must carry session id, session token, case id, chunk index, audio offsets, and PCM bytes.
- R3: PCM bytes must be transferred in a structured safe form, such as base64 in JSON, without uploading outside localhost.
- R4: Backend partial/final responses must be normalized into the existing accepted/ignored gate events so all existing gate metrics still work.
- R5: Transport failures or malformed responses must produce explicit local errors rather than silently passing.
- R6: The CLI must reject `http-json` runs without a service URL.
- R7: Existing fake adapters must continue to pass their self-tests unchanged.
- R8: A controlled local fake service must prove that a process-boundary HTTP service can pass the same gate.
- R9: The feature must not claim any real ASR model has passed until a separate model service feature runs through this adapter.

## Constraints

- The adapter must stay backend-neutral and not import Qwen3, MiMo, FunASR, or MLX model code.
- The adapter must not weaken cancel, stale-session, late-partial, final-after-stop, or partial-before-stop checks.
- The feature must remain reproducible with standard Python libraries.

## Dependencies

- `2026-06-22-asr-backend-selection-roadmap`
- `2026-06-22-incremental-ux-asr-gate`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/system_overview.md`
