# Plan — Fun-ASR-Nano Local Evaluation Adapter

## Implementation sequence

1. Create the SDD feature contract and feature matrix entry.
2. Add a `funasr-nano-local` adapter to `eval/asr_streaming/run_eval.py`.
3. Keep the adapter file-level first: one final event, no fake partials.
4. Add CLI options for language, device, model name, and VAD segment length if needed.
5. Update `model_registry.json` so `fun-asr-nano-2512` points to the adapter once implemented.
6. Update README with the smoke-test command.
7. Run non-server validation.
8. Run a one-case local smoke test.
9. If smoke passes and runtime is acceptable, run all 10 pilot cases.

## Touched areas

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/README.md`
- `specs/2026-06-20-fun-asr-nano-local-eval/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation implementation notes

- Required before smoke:
  - `python3 -m py_compile eval/asr_streaming/run_eval.py`
  - `python3 -m json.tool eval/asr_streaming/model_registry.json`
  - `bash eval/asr_streaming/validate.sh`
- Required smoke:
  - Run one short local WAV through `--adapter funasr-nano-local --model-id fun-asr-nano-2512`.
- Optional full benchmark:
  - Run all 10 pilot WAVs if the one-case smoke run completes without dependency/runtime blockers.

## PMB promotion candidates

- Promote only after the adapter produces validated local results and the operating pattern becomes durable.

## Risks and mitigations

- Risk: Fun-ASR-Nano direct AutoModel path may be CUDA-oriented or too slow on Mac CPU/MPS.
  Mitigation: Treat this pass as feasibility first; record blockers instead of forcing production integration.
- Risk: First run may download large model files.
  Mitigation: Keep this behind explicit candidate evaluation commands and document the local cache behavior.
- Risk: File-level adapter lacks realtime partial behavior.
  Mitigation: Mark partial metrics as unavailable and use this as quality/runtime screening before any streaming service work.
