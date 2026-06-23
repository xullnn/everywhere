# Validation - Qwen3-ASR MLX Cumulative Recompute Probe

## Completion Rule

This feature can be marked `passes=true` only when the probe script compiles, self-tests pass, the ASR harness validation passes, and at least one local Qwen3-ASR MLX model is probed or explicitly recorded as unavailable.

## Acceptance Criteria

- A1: The probe self-test proves cumulative recompute is never marked native realtime eligible.
- A2: Runtime output includes prefix latency, serial queue latency, serial recompute RTF, prefix rewrite rate, final CER/WER, and Chinese metric explanations.
- A3: Runtime output distinguishes wrapper viability from realtime gate eligibility.
- A4: Case filtering supports running `zh_short_001` and a long case independently.
- A5: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_probe.py
python3 eval/asr_streaming/qwen3_mlx_cumulative_probe.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-qwen3-mlx-cumulative-recompute-probe/feature.json >/dev/null
```

## Runtime Probe

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_cumulative_probe.py run \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --language Chinese \
  --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-smoke-20260622
```

Long-form diagnostic:

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_cumulative_probe.py run \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.local.jsonl \
  --case-id long_120_001 \
  --language Chinese \
  --max-prefixes 8 \
  --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-long120-20260622
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature does not change Swift code.
- Running the 1.7B cumulative probe is optional after the 0.6B probe establishes feasibility.

## Evidence Required In `specs/progress.md`

- Commands run and result summaries.
- Output directories.
- Explicit native realtime eligibility and wrapper viability conclusion.
