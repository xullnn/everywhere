# Validation - Qwen3-ASR MLX HTTP Service Boundary

## Completion Rule

This feature can be marked `passes=true` only when the HTTP service compiles, fake-backend process-boundary gate passes, existing eval harness validation passes, and real Qwen3 0.6B MLX HTTP gate smoke either passes or is explicitly recorded as blocked by unavailable local model/runtime.

## Acceptance Criteria

- A1: `qwen3_mlx_http_service.py` compiles.
- A2: `qwen3_mlx_cumulative_service.py` self-test still passes.
- A3: `incremental_ux_gate.py` self-test still passes.
- A4: The new HTTP service can pass `incremental_ux_gate.py --adapter http-json` in fake-backend mode.
- A5: The service uses gate-provided session tokens in returned partial/final events.
- A6: If local Qwen3 0.6B MLX runtime is available, real-model smoke passes through `http-json` with pre-stop partial and post-stop final.
- A7: Existing `bash eval/asr_streaming/validate.sh` passes.
- A8: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/qwen3_mlx_http_service.py
python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_service.py
python3 eval/asr_streaming/qwen3_mlx_cumulative_service.py self-test
python3 eval/asr_streaming/incremental_ux_gate.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-23-qwen3-mlx-http-service-boundary/feature.json >/dev/null
```

## HTTP Gate Smokes

Fake-backend smoke:

```bash
python3 eval/asr_streaming/qwen3_mlx_http_service.py --fake-backend --host 127.0.0.1 --port 18105
python3 eval/asr_streaming/incremental_ux_gate.py run \
  --adapter http-json \
  --service-url http://127.0.0.1:18105 \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-mlx-http-service-fake-smoke-20260623
```

Real Qwen3 0.6B MLX smoke:

```bash
bash scripts/run_qwen3_mlx_http_gate_smoke.sh
```

Optional long-form HTTP gate:

```bash
CASES=eval/asr_streaming/cases.long120.local.jsonl \
OUT_DIR=eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-long120-20260623 \
bash scripts/run_qwen3_mlx_http_gate_smoke.sh
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature must not change Swift code.
- Real long-form Qwen3 HTTP gate beyond smoke is recommended but may be recorded as follow-up if runtime cost is too high in this pass.

## Evidence Required In `specs/progress.md`

- Commands run and pass/fail/skipped results.
- Fake HTTP smoke result directory.
- Real Qwen3 HTTP smoke result directory or blocker reason.
- Explicit statement that Swift runtime files were not changed.
