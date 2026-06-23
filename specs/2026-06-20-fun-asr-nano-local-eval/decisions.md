# Decisions — Fun-ASR-Nano Local Evaluation Adapter

## Confirmed decisions

- D1: Start with a file-level local adapter using existing WAV files; do not change the macOS app runtime.
- D2: Treat realtime streaming/vLLM service work as a follow-up unless direct local evaluation proves the model is worth deeper integration.
- D3: Use `--model-id fun-asr-nano-2512` so all result directories are self-describing.
- D4: Do not synthesize partial events for a file-level backend; partial latency and partial event counts should remain unavailable or zero.
- D5: Default the local file-level adapter to no VAD on FunASR 1.3.1. `fsmn-vad` loads, but `AutoModel.inference_with_vad` raises `KeyError(0)` when merging VAD segments with Fun-ASR-Nano results.
- D6: Use the installed `funasr.models.fun_asr_nano.model.py` as `remote_code` when the model repo lacks `model.py`.

## Open questions / unresolved choices

- Whether the model quality gain is strong enough to justify a later streaming service adapter.
- Whether a newer FunASR runtime fixes the Nano + VAD merge bug.
- Whether MPS or GGUF/llama.cpp paths give better realtime deployment characteristics than CPU `AutoModel`.

## PMB promotion candidates

- Promote the selected Fun-ASR-Nano operating pattern only after validated local results and stable commands exist.
