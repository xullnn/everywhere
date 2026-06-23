# Decisions - Qwen3-ASR Local Evaluation Adapter

## Confirmed decisions

- D1: Start with Qwen3-ASR 0.6B because it has lower model size and runtime risk than 1.7B.
- D2: Use a file-level transformers-backend adapter first; do not touch the macOS app runtime.
- D3: Treat Qwen3-ASR 1.7B as a follow-up after 0.6B proves the local path.
- D4: Treat vLLM streaming as a follow-up because official streaming support is vLLM-based and likely CUDA-oriented.
- D5: Do not use DashScope/API paths for evaluation because this project requires local/offline validation.
- D6: Install the lean transformers runtime by default instead of the full `qwen-asr` demo dependency set; the full package pulls Gradio/Flask demo tools that are not needed for file-level eval.
- D7: The `qwen-asr` runtime and Qwen3-ASR 0.6B model can complete at least one local WAV smoke run through the CPU file-level adapter.
- D8: Use `curl --continue-at -` for `model.safetensors` after ModelScope `snapshot_download` stalls; keep `snapshot_download` only for metadata and small files.
- D9: Treat the validated 0.6B path as file-level screening evidence only; it does not validate realtime partial behavior or the app runtime.

## Open questions / unresolved choices

- Whether Qwen3-ASR 0.6B CPU file-level latency is acceptable enough for broader screening, or whether MPS/runtime optimization is needed before full-case evaluation.
- Whether MPS is reliable enough for Qwen3-ASR on this machine or CPU should be the stable baseline.
- Whether Qwen3-ASR improves the technical/product term failures seen in Fun-ASR-Nano.

## PMB promotion candidates

- Promote the Qwen3-ASR operating pattern only after local smoke or documented local blocker is validated.
