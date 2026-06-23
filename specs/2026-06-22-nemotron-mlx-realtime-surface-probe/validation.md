# Validation - Nemotron MLX Realtime Surface Probe

## Completion Rule

This feature can be marked `passes=true` only when the ASR harness validation passes, feature metadata JSON is valid, and the local Nemotron MLX runtime surface probe completes with a recorded summary.

## Acceptance Criteria

- A1: The local probe loads the Nemotron MLX snapshot without editing vendored source.
- A2: Probe output records `generate`, `stream_generate`, `stream_transcribe`, `generate_streaming`, and `create_streaming_session` availability.
- A3: Probe output marks `realtime_gate_eligible=false` if no session API is present.
- A4: Registry and feasibility notes state that `stream_generate(audio)` is not equivalent to microphone PCM feed semantics.

## Automated Checks

```bash
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null
python3 -m json.tool specs/2026-06-22-nemotron-mlx-realtime-surface-probe/feature.json >/dev/null
```

## Runtime Probe

```bash
PYTHONPATH=.external/repos/mlx-audio-main-src/mlx-audio-main /usr/bin/time -l .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_realtime_probe.py probe \
  --model-id nemotron-3.5-asr-streaming-0.6b-mlx-8bit \
  --model .external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit \
  --mlx-audio-source .external/repos/mlx-audio-main-src/mlx-audio-main \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --language zh-CN \
  --out-dir eval/asr_streaming/results/nemotron-mlx-realtime-surface-probe-20260622
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature does not change Swift code.
- Full realtime gate execution is not applicable because no session API is exposed.

## Evidence Required In `specs/progress.md`

- Commands run and result summaries.
- Output directory.
- Explicit realtime-gate eligibility conclusion.
