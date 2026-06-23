# Decisions - GLM-ASR-Nano Local Evaluation Adapter

## Confirmed decisions

- D1: Use a file-level adapter first and keep GLM separate from macOS app runtime integration.
- D2: Use a separate `.venv-glm-asr` runtime because the existing Qwen3 venv's Transformers version does not include GLM-ASR classes.
- D3: Prefer the model repository's Transformers API from the local README over guessed inference code.
- D4: Use `transformers==5.12.1` in `.venv-glm-asr`; it exposes `GlmAsrForConditionalGeneration` and `GlmAsrProcessor` locally.
- D5: Treat GLM-ASR-Nano as runnable but lower priority than Qwen3-ASR on the current 10-case local file-level evidence.

## Open questions

- Whether GLM-ASR-Nano has a practical realtime streaming or partial-output path on this macOS target. The current adapter is file-level only.
