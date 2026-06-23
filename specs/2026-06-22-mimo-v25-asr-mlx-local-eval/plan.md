# Plan - MiMo-V2.5-ASR MLX Local Evaluation Adapter

## Implementation sequence

1. Confirm both MiMo ASR and audio tokenizer model directories are complete locally.
2. Install MLX and `mlx-audio[stt]` into `.venv-mimo`.
3. Run the upstream helper script against one local WAV case as a load smoke test.
4. Add a minimal `mimo-asr-mlx-local` file-level adapter to the eval harness.
5. Run a one-case harness smoke test.
6. Run the full 10-case local WAV set if smoke passes.
7. Record validation evidence and aggregate metrics in `specs/progress.md`.

## Touched areas

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-mimo-v25-asr-mlx-local-eval/`

## Validation implementation notes

- Reuse existing case loading, normalization, metric, and summary-writing paths.
- Keep the adapter file-level and explicitly mark that it does not provide realtime partials.
- Use `.venv-mimo/bin/python` for MiMo validation so MLX dependencies stay separate from Qwen, GLM, FireRed, and FunASR runtimes.

## Risks and mitigations

- Risk: MLX or `mlx-audio` dependency versions may fail on the local macOS/Python version.
  Mitigation: Use an isolated `.venv-mimo`; record the concrete blocker if runtime cannot load.
- Risk: The first run includes cold model load time.
  Mitigation: Interpret smoke latency separately from full-run per-case timings where the model is reused.
- Risk: File-level quality looks good but realtime partial support is absent.
  Mitigation: Keep app integration as a separate follow-up after backend selection.

## PMB promotion candidates

- None until MiMo evaluation results are validated and durable.
