# Requirements - Realtime ASR Streaming Gate

## Problem

Recent ASR candidate tests mixed two different questions: file-level final transcription quality and realtime microphone-style transcription behavior. LocalVoiceInput requires realtime partials for the floating panel, so a model that only transcribes a complete WAV file must not be ranked as a realtime backend candidate.

## Scope

### IN

- Add an independent realtime gate under `eval/asr_streaming/`.
- Use existing WAV cases to simulate microphone input by sending timed PCM chunks.
- Start with the current FunASR WebSocket 2pass baseline as the known true-streaming adapter.
- Record per-case evidence for chunk input, partial timing, final timing, event ordering, coverage, and pass/fail reasons.
- Keep Chinese explanations for all key metric abbreviations.

### OUT

- Do not change the Swift macOS app runtime.
- Do not change hotkeys, focus detection, clipboard, paste engine, floating panel, or correction pipeline.
- Do not treat complete-audio `generate(...)` adapters as realtime just because they can stream tokens after the whole file is loaded.
- Do not introduce cloud ASR, upload paths, LLM correction, or auto-send behavior.

## Requirements

- R1: The gate must require at least one partial event before simulated user stop.
- R2: The gate must treat user stop, not backend intermediate offline/final segments, as the point after which final output is evaluated, and it must require at least one final/offline event after user stop.
- R3: The gate must flag late partial events after final.
- R4: The gate must write per-case `events.jsonl`, `chunks.jsonl`, and `summary.json`.
- R5: The aggregate `summary.json` must include pass/fail counts, reason counts, CER, WER, RTF, latency, partial cadence, and Chinese metric explanations.
- R6: The first implementation must support `funasr-ws`; other adapters are follow-up only after they expose an equivalent session contract.
- R7: Validation must run without requiring a live ASR server via a self-test path.

## Constraints

- All testing remains local after model dependencies are installed.
- Existing file-level evaluation results remain valid as final-quality evidence, but they are not realtime integration evidence.
- The current app requirement remains partial in floating panel only; no partial text is written into the active input field.

## Dependencies

- `specs/2026-06-20-asr-backend-eval-harness`
- `specs/2026-06-22-asr-runtime-feasibility-comparison`
- `specs/2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
