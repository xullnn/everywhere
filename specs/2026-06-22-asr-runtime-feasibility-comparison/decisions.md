# Decisions - ASR Runtime Feasibility Comparison

## Confirmed decisions

- D1: Compare candidates for backend runtime feasibility before changing the macOS app.
- D2: Keep the app output safety layer unchanged; backend selection must not affect paste/copy safety behavior.
- D3: Treat realtime partial capability as a hard integration concern for the current floating-panel MVP.
- D4: MiMo-V2.5-ASR MLX is the strongest file-level candidate on the current 10 local WAV cases, but it is not selected as the app runtime because the inspected MiMo MLX class only exposes `generate(...)` and no streaming or chunked partial API.
- D5: Official Qwen3-ASR exposes streaming session methods, but the local source requires the vLLM backend for streaming and the current `.venv` does not have `vllm` installed.
- D6: The official Qwen3-ASR vLLM install path is CUDA-oriented in the bundled README, so MacBook Pro M4 local feasibility remains unproven.
- D7: `mlx-audio` includes Qwen3-ASR MLX 8-bit models and token streaming APIs; this is the best next Apple Silicon runtime spike, but it is not yet locally downloaded or evaluated.
- D8: The next backend work should stay outside the Swift app and validate a local service simulation with WAV-driven timed PCM chunks before app integration.

## Open questions / unresolved choices

- Whether `mlx-community/Qwen3-ASR-0.6B-8bit` matches the official Qwen3-ASR 0.6B quality closely enough on the local 10-case set.
- Whether Qwen3-ASR MLX token streaming can be adapted to a true microphone chunk service, or whether it only helps after a full audio buffer is available.
- Whether MiMo MLX can provide practical chunked or partial output without retracing the whole audio file.
- Dedicated steady-state RSS and cold-start numbers are still needed for Qwen3-ASR 0.6B MLX, Qwen3-ASR 1.7B MLX if tested, and any long-running service process.
- Whether a hotword/context post-correction layer should be added before runtime integration or after backend selection.

## PMB promotion candidates

- Promote the selected ASR backend service contract only after a runtime spike validates realtime partials, final output behavior, memory, and local-only operation.
