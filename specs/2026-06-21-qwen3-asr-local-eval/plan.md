# Plan - Qwen3-ASR Local Evaluation Adapter

## Implementation sequence

1. Create the SDD feature contract and feature matrix entry.
2. Inspect official Qwen3-ASR usage and current local Python environment.
3. Add a `qwen3-asr-local` file-level adapter to `eval/asr_streaming/run_eval.py`.
4. Add CLI options for Qwen3-ASR model path/name, device, dtype, language, max tokens, and local-files-only behavior.
5. Update `model_registry.json` to point `qwen3-asr-0.6b` at the new adapter.
6. Add scripts for Qwen3-ASR dependency setup/download and one-case smoke.
7. Update eval README with the Qwen3-ASR commands and the file-level limitation.
8. Run non-runtime checks.
9. Run dependency setup and a one-case smoke if the local runtime can load on this Mac.
10. Run the full 10-case benchmark only after smoke passes.

## Touched areas

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/README.md`
- `scripts/setup_qwen3_asr_venv.sh`
- `scripts/download_qwen3_asr.sh`
- `scripts/run_qwen3_asr_smoke.sh`
- `specs/2026-06-21-qwen3-asr-local-eval/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation implementation notes

- Required non-runtime checks:
  - `python3 -m py_compile eval/asr_streaming/run_eval.py`
  - `python3 -m json.tool eval/asr_streaming/model_registry.json`
  - `python3 -m json.tool specs/feature_matrix.json`
  - `bash -n scripts/setup_qwen3_asr_venv.sh scripts/download_qwen3_asr.sh scripts/run_qwen3_asr_smoke.sh`
  - `bash eval/asr_streaming/validate.sh`
- Required smoke if dependencies/model load:
  - `DRY_RUN=1 bash scripts/run_qwen3_asr_smoke.sh`
  - `bash scripts/run_qwen3_asr_smoke.sh`
- Preferred full benchmark:
  - Run all 10 pilot WAVs through `qwen3-asr-local` after smoke passes.

## PMB promotion candidates

- Promote only after validated local results show a stable operating pattern or blocker that should guide future backend choices.

## Risks and mitigations

- Risk: `qwen-asr` may require Python 3.12 or CUDA-oriented defaults.
  Mitigation: Try the transformers backend with explicit CPU/MPS options; record a blocker if the official local path is not viable.
- Risk: Qwen3-ASR model download may be slow or large.
  Mitigation: Separate download from smoke and keep resumable/manual retry commands documented.
- Risk: File-level inference does not prove realtime partial latency.
  Mitigation: Treat this as model quality/runtime screening only.
