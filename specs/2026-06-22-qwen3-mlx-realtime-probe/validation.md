# Validation - Qwen3-ASR MLX Realtime Probe

## Completion Rule

This feature can be marked `passes=true` only when the probe script compiles, self-tests pass, the ASR harness validation passes, and at least one Qwen3-ASR MLX local model is probed or explicitly recorded as unavailable.

## Acceptance Criteria

- A1: The self-test rejects token-stream-only models as realtime-gate eligible.
- A2: The self-test accepts a fake model with `create_streaming_session` as realtime-gate eligible.
- A3: Runtime probe output records method signatures and missing session API.
- A4: Prefix diagnostic, if run, is clearly labeled as not equivalent to a realtime gate pass.
- A5: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/qwen3_mlx_realtime_probe.py
python3 eval/asr_streaming/qwen3_mlx_realtime_probe.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-qwen3-mlx-realtime-probe/feature.json >/dev/null
```

## Runtime Probe

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_realtime_probe.py probe \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --language Chinese \
  --run-prefix-smoke \
  --out-dir eval/asr_streaming/results/qwen3-mlx-realtime-probe-0.6b-smoke-20260622
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature does not change Swift code.
- Running the 1.7B probe is optional after the 0.6B probe establishes the API-surface behavior.

## Evidence Required In `specs/progress.md`

- Commands run and result summaries.
- Probe output directory.
- Explicit statement of realtime-gate eligibility.
