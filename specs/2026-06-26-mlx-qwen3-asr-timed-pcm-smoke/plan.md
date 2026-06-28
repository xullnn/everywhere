# Plan - mlx-qwen3-asr Timed PCM Smoke

## Implementation Sequence

1. Create this SDD feature contract and add it to `specs/feature_matrix.json`.
2. Inspect the local `mlx-qwen3-asr` streaming/session source to confirm API signatures and state fields.
3. Add `eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py`.
4. Reuse existing case loading, WAV validation, CER/WER, JSON, and metric helpers from `eval/asr_streaming/run_eval.py`.
5. Implement result capture:
   - source/package metadata;
   - model load status;
   - per-case chunk feed timings;
   - partial events before finish;
   - final output after finish;
   - latency and quality metrics;
   - eligibility classification.
6. Add documentation to `eval/asr_streaming/README.md`.
7. Run syntax, dry-run, and local smoke checks if the model/source/runtime are compatible.
8. Record concrete evidence in `specs/progress.md`.

## Touched Areas

- `specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/*`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py`
- `eval/asr_streaming/README.md`

## Validation Implementation Notes

- Prefer `.venv-mimo/bin/python` for real smoke because the default Python may not have MLX installed.
- A model format mismatch is not a script failure if it is captured in structured output and progress evidence.
- Realtime sleep should be configurable; non-sleep mode is useful for compatibility checks but does not prove user-perceived realtime pacing.
- Keep the default first local smoke small enough to avoid blocking the session; long cases can be run after compatibility is proven.

## PMB Promotion Candidates

- Only after validation: durable conclusion about whether `mlx-qwen3-asr` supports a locally useful stateful PCM streaming route for LocalVoiceInput.

## Risks And Mitigations

- Risk: The community package cannot load the existing `mlx-community__Qwen3-ASR-0.6B-8bit` snapshot.
  Mitigation: classify as model-format/load incompatibility and keep the current Qwen3 HTTP cumulative path unchanged.
- Risk: The API emits only final text or updates too slowly.
  Mitigation: record as realtime gate failure without app integration.
- Risk: Real timed playback takes too long.
  Mitigation: support `--case-limit`, `--only-id`, and non-realtime compatibility mode.
