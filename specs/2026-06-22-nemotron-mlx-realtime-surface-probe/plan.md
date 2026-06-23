# Plan - Nemotron MLX Realtime Surface Probe

## Implementation Sequence

1. Reuse `eval/asr_streaming/qwen3_mlx_realtime_probe.py` for API-surface classification.
2. Add a narrow local loader shim for `model_type=nemotron_asr` when the implementation exists but the STT loader remapping is missing.
3. Run the surface probe against the local Nemotron 0.6B 8-bit MLX snapshot.
4. Update registry, runtime feasibility notes, PMB, and progress evidence.

## Touched Areas

- `eval/asr_streaming/qwen3_mlx_realtime_probe.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/runtime_feasibility.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-nemotron-mlx-realtime-surface-probe/*`

## Risk Controls

- The shim mutates only the in-process `MODEL_REMAPPING` dictionary and only for known model types.
- The probe does not modify external dependency source.
- Runtime evidence remains outside the Swift app.

## PMB Promotion Candidates

- Promote the stable conclusion that local Nemotron MLX has cache-aware `stream_generate(audio)` but no session-style incremental PCM API.
