# Plan - Realtime ASR Streaming Gate

## Implementation Steps

1. Create `eval/asr_streaming/realtime_gate.py`.
2. Reuse existing case loading, model registry, WAV validation, transcript aggregation, and core metric helpers from `run_eval.py`.
3. Implement a strict FunASR WebSocket gate runner that:
   - sends 16 kHz mono int16 PCM in timed chunks,
   - records every sent chunk,
   - records every backend partial/final event,
   - waits for user-stop simulation before final gate evaluation.
4. Add self-tests for:
   - passing realtime partial/final behavior,
   - late partial after final rejection,
   - complete-file-only final rejection.
5. Add documentation and include the gate in `eval/asr_streaming/validate.sh`.
6. Record SDD status and validation evidence.

## Files To Change

- `eval/asr_streaming/realtime_gate.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-realtime-streaming-gate/*`

## Non-Goals

- No Swift app runtime integration.
- No new model download in this feature.
- No cloud or network ASR dependency except connecting to a locally running FunASR WebSocket server when manually running the gate.
