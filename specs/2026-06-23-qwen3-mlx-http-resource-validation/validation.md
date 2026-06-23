# Validation - Qwen3-ASR MLX HTTP Resource And Extended Gate Validation

## Completion Rule

This feature can be marked `passes=true` only when the new scripts compile, existing eval harness validation passes, and the extended Qwen3 0.6B MLX HTTP gate either passes or is explicitly recorded as blocked by unavailable local runtime/model files.

## Acceptance Criteria

- A1: `monitor_pid_resources.py` compiles.
- A2: Existing `bash eval/asr_streaming/validate.sh` passes.
- A3: The extended runner starts and stops the Qwen3 HTTP service cleanly.
- A4: The extended runner writes gate `summary.json`, `resource_samples.jsonl`, `resource_summary.json`, and `run_metadata.json`.
- A5: Resource summary includes peak/mean RSS and peak/mean CPU.
- A6: If local Qwen3 0.6B MLX runtime is available, the extended gate runs on `long_200_001`, `long_400_001`, and `long_code_switch_001`.
- A7: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/monitor_pid_resources.py
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-23-qwen3-mlx-http-resource-validation/feature.json >/dev/null
```

## Extended Gate

```bash
bash scripts/run_qwen3_mlx_http_extended_gate.sh
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature must not change Swift code.
- Manual app testing is not applicable; this feature is eval-harness only.

## Evidence Required In `specs/progress.md`

- Commands run and pass/fail/skipped results.
- Extended gate result directory.
- Aggregate gate metrics and case-level pass/fail count.
- Resource peak/mean RSS and CPU.
- Explicit statement that Swift runtime files were not changed.
