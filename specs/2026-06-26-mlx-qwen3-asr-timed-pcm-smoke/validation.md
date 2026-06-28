# Validation - mlx-qwen3-asr Timed PCM Smoke

## Completion Rule

This feature can be marked `passes=true` only when the timed PCM probe exists, syntax/dry-run checks pass, and either a real local smoke result or a structured compatibility blocker is recorded in `specs/progress.md`.

## Acceptance Criteria

- A1: The probe writes a JSON summary under `eval/asr_streaming/results/`.
- A2: Dry-run succeeds without importing or loading `mlx-qwen3-asr`.
- A3: The script can import the local source checkout when `--source-dir .external/repos/mlx-qwen3-asr` is supplied.
- A4: Real smoke attempts use 16 kHz mono int16 WAV cases and call `init_streaming/feed_audio/finish_streaming`.
- A5: Per-case summaries record partial-before-stop count, final-after-stop output, TTFP, partial cadence, final latency, RTF, CER, WER, partial stability, rewrite rate, and finalization delta when available.
- A6: The final summary states whether the candidate is `local_voice_input_realtime_eligible_now`.
- A7: Any failure records a category such as `import_failed`, `model_load_failed`, `api_failed`, or `gate_failed`.
- A8: Generated metric explanations include Chinese descriptions for all key abbreviations.
- A9: Per-case summaries distinguish `timed_pcm_gate_passed` from `selection_gate_passed`.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py
python3 eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py --dry-run --out-dir eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-dry-run
.venv-mimo/bin/python eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py --source-dir .external/repos/mlx-qwen3-asr --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.long_prepared.local.jsonl --case-limit 1 --no-realtime-sleep --out-dir eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-smoke
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/feature.json >/dev/null
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are not required because this feature must not touch Swift code.
- Full 3-case long timed replay is optional until the one-case compatibility smoke succeeds.
- Realtime-paced playback is optional in the first compatibility pass; it becomes required before claiming user-facing realtime eligibility.

## Evidence Required In `specs/progress.md`

- Commands run.
- Result status.
- Result directory paths.
- Eligibility conclusion.
- Failure category and blocker if a real local smoke cannot complete.
