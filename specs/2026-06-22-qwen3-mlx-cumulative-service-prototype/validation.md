# Validation - Qwen3-ASR MLX Cumulative Service Prototype

## Completion Rule

This feature can be marked `passes=true` only when all required automated checks pass and at least one runtime Qwen3-ASR MLX service probe is completed or explicitly recorded as unavailable.

## Acceptance Criteria

- A1: Self-test proves old session partial/final jobs are ignored after a new session starts with the same session id.
- A2: Self-test proves late partials after `finish` do not overwrite or append after final.
- A3: Self-test proves `cancel` produces no final and no post-cancel partial/final output.
- A4: Runtime service output includes partial events before simulated user stop and final output after stop for the tested case.
- A5: Runtime service output includes first usable partial latency, final latency, partial cadence, final CER/WER, ignored stale event count, and Chinese metric explanations.
- A6: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_service.py
python3 eval/asr_streaming/qwen3_mlx_cumulative_service.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-qwen3-mlx-cumulative-service-prototype/feature.json >/dev/null
```

## Runtime Probe

```bash
PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_cumulative_service.py run \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --language Chinese \
  --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-smoke-20260622
```

Long-form diagnostic:

```bash
PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_cumulative_service.py run \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.local.jsonl \
  --case-id long_120_001 \
  --language Chinese \
  --max-prefixes 8 \
  --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-long120-20260622
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature does not change Swift code.
- A network server process is optional; this feature validates the service contract in-process first.

## Evidence Required In `specs/progress.md`

- Commands run and result summaries.
- Output directories.
- Explicit statement of service gate status and native realtime eligibility.
