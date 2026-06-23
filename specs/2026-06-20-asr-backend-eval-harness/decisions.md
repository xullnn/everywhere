# Decisions — ASR Backend Evaluation Harness

## Confirmed decisions

- D1: Use recording files to simulate realtime input instead of relying on repeated manual dictation.
- D2: Treat public benchmark results as shortlist evidence, not as final product validation.
- D3: Keep the first harness pass independent from macOS UI, hotkey, focus, clipboard, and paste code.
- D4: Implement the existing FunASR WebSocket backend first because it is the current local ASR baseline and matches the app architecture.
- D5: Keep Qwen3-ASR, MiMo-V2.5-ASR, FireRed, and GLM as candidate follow-ups until local runtime feasibility is confirmed.
- D6: The current FunASR WebSocket baseline smoke run passed with the bundled sample WAV; this validates harness plumbing, not broader ASR quality.
- D7: Long-form FunASR 2-pass runs can return incomplete `2pass-offline` segments for a whole user recording. The eval harness must retain raw events, expose offline segment coverage, and mark/handle short offline finals instead of treating the first or concatenated offline text as guaranteed complete.
- D8: Future ASR result reviews must not rely on unexplained abbreviations. Result JSON should carry Chinese metric explanations, and every tested model should include supplier, parameter scale, and release-date metadata with uncertainty marked when exact first-party dates are not verified.

## Open questions / unresolved choices

- Which user-provided recordings should become the first project-specific regression set.
- Whether Qwen3-ASR should be tested through vLLM, Transformers, MLX conversion, or another Mac-friendly runtime.
- Whether Fun-ASR-Nano should be tested through FunASR Python, vLLM WebSocket, or a GGUF/llama.cpp path on M4.

## PMB promotion candidates

- Promote the final ASR evaluation operating pattern only after a real audio/server run validates the harness.
