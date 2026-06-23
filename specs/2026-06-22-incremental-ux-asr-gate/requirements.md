# Requirements - Incremental UX ASR Gate

## Problem

LocalVoiceInput needs to choose a local ASR backend for user-perceived realtime dictation: text should accumulate in the floating panel while the user is speaking, and a better final transcript should be available after user stop.

Existing evidence is split across file-level final transcription, FunASR WebSocket realtime behavior, and an in-process Qwen3-ASR MLX cumulative recompute prototype. Those results cannot be compared directly until candidate backends share a single timed PCM input contract and a single set of user-experience metrics.

## Scope

### IN

- Add a backend-neutral incremental UX gate for local ASR backend prototypes.
- Simulate microphone input from existing 16 kHz mono int16 WAV cases using timed PCM chunks.
- Require a common session contract: start, push PCM, partial events, finish, final event, cancel, and stale event rejection.
- Include fake adapters that prove the gate accepts valid incremental behavior and rejects file-only, late partial, cancel leakage, and stale-session behavior.
- Produce per-case and aggregate JSON summaries with Chinese metric explanations.
- Keep the feature isolated to the eval harness and SDD documentation.

### OUT

- No Swift App runtime integration.
- No macOS hotkey, focus, paste, clipboard, or floating-panel changes.
- No InputMethodKit work.
- No cloud ASR dependency or audio/text upload.
- No default LLM correction.
- No real Qwen3 local service process boundary in this feature; that is a follow-up.
- No MiMo runtime probe in this feature; that is a follow-up.

## Requirements

- R1: The gate must replay WAV audio as ordered PCM chunks and record chunk traces separately from backend events.
- R2: The gate must support real wall-clock pacing by default and a non-realtime diagnostic mode for fast self-tests.
- R3: The backend protocol must expose session ownership and event ordering enough to detect stale events and late partials.
- R4: A backend must emit at least one partial before simulated user stop to pass the incremental UX gate.
- R5: A backend must emit a final after simulated user stop to pass the gate.
- R6: A backend must reject or ignore partial/final output after cancel.
- R7: A backend must ignore old-session events when a newer session owns the same logical session id.
- R8: A complete-audio final-only backend must fail the gate even when final CER/WER is good.
- R9: Summaries must include CER, WER, RTF where applicable, first partial latency, partial cadence, final latency, partial rewrite rate, final coverage, and gate failure reasons.
- R10: All metric abbreviations in produced summaries must include Chinese explanations.

## Constraints

- The gate must remain local and offline.
- It must not weaken existing product safety logic around partial text, final output, paste, focus, or clipboard behavior.
- It must not classify cumulative recompute as native realtime streaming.
- It must keep file-level quality evidence separate from incremental UX evidence.

## Dependencies

- `2026-06-20-asr-backend-eval-harness`
- `2026-06-22-realtime-streaming-gate`
- `2026-06-22-qwen3-mlx-cumulative-service-prototype`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/system_overview.md`
