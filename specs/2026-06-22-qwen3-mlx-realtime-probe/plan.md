# Plan - Qwen3-ASR MLX Realtime Probe

## Implementation Sequence

1. Add `eval/asr_streaming/qwen3_mlx_realtime_probe.py`.
2. Reuse existing case loading, WAV validation, CER/WER, model metadata, and JSON helpers from `run_eval.py`.
3. Implement API-surface classification:
   - true session API: `create_streaming_session`
   - file/token streaming: `stream_transcribe`, `stream_generate`, or `generate(..., stream=True)`
4. Add an optional prefix-audio diagnostic using the first N seconds of a WAV.
5. Add self-test coverage for classification logic.
6. Document the command and record validation evidence.

## Touched Areas

- `eval/asr_streaming/qwen3_mlx_realtime_probe.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-qwen3-mlx-realtime-probe/*`

## Risk Controls

- The probe will not mark prefix/cumulative recompute as realtime gate success.
- Runtime checks remain outside the Swift app.
- Heavy model loading is not part of the default validation script.
