# Decisions - MiMo-V2.5-ASR MLX Local Evaluation Adapter

## Confirmed decisions

- D1: Evaluate MiMo-V2.5-ASR MLX as an independent file-level backend candidate first.
- D2: Keep MiMo separate from the macOS app runtime until local quality and runtime feasibility are known.
- D3: Use the `mlx-audio.stt.load` path used by the community helper script.
- D4: Use `.venv-mimo` so MLX dependencies do not disturb existing Qwen, GLM, FireRed, or FunASR eval runtimes.
- D5: Treat first-run cold-load latency separately from steady per-case inference timing.
- D6: Treat MiMo-V2.5-ASR MLX as the current best file-level candidate on the 10 local WAV set, but do not select it as the app runtime until a realtime/streaming partial path is investigated.

## Open questions

- Whether MiMo has or can support a practical realtime partial path for floating-panel updates.
- Whether the MLX int4 conversion is the right runtime target compared with full-precision or 8-bit variants.
- Whether a hotword/context biasing layer can fix recurring project-name and model-name errors without using a cloud or LLM correction path.

## PMB promotion candidates

- None yet.
