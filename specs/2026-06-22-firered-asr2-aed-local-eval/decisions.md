# Decisions - FireRedASR2-AED Local Evaluation Adapter

## Confirmed decisions

- D1: Evaluate FireRedASR2-AED as an independent file-level backend candidate first.
- D2: Keep FireRed separate from the macOS app runtime until local quality and runtime feasibility are known.
- D3: Prefer the official `FireRedASR2S` inference code over guessed model-loading code.
- D4: Use a separate `.venv-firered` runtime that reuses the existing macOS torch stack and installs only missing FireRed dependencies.
- D5: Keep `return_timestamp=false` for the current file-level adapter to avoid adding torchaudio forced-alignment cost to first-pass ASR screening.
- D6: Treat FireRedASR2-AED as locally runnable but not a near-term default backend candidate for the MVP because long-form CPU latency is worse than Qwen3-ASR and GLM-ASR-Nano.

## Open questions

- Whether a non-CPU FireRed runtime path, such as MPS or an optimized serving path, can reduce long-form latency enough to matter for this Mac MVP.

## PMB promotion candidates

- None yet.
