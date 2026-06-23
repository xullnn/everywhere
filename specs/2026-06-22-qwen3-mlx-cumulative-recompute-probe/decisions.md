# Decisions - Qwen3-ASR MLX Cumulative Recompute Probe

## Confirmed Decisions

- D1: Cumulative recompute is an engineering workaround, not native session streaming.
- D2: A cumulative recompute result can justify a future service prototype only if latency, queueing, and text stability look acceptable on local WAV cases.
- D3: The current feature will not modify the Swift macOS app or mark Qwen3-ASR MLX as realtime-gate eligible.
- D4: The first required runtime probe targets `qwen3-asr-0.6b-mlx-8bit`; 1.7B remains optional because the previous realtime surface probe showed the same missing session API.
- D5: The 0.6B cumulative recompute probe is promising on smoke and `long_120_001`, but the project still treats it as wrapper feasibility evidence only, not realtime gate success.
- D6: Punctuation-only prefix output such as `。` is not counted as a usable simulated partial; usable partials must contain normalized text content.

## Open Questions / Unresolved Choices

- Whether a future service should use cumulative recompute, a model with native session API, or a modified Qwen3 MLX implementation with cached audio encoder state.
- Whether a lower prefix step such as 500ms is useful after the 1s-step feasibility probe.
- Whether 1.7B cumulative recompute gives enough quality gain to justify the larger local model and slower file-level baseline.

## PMB Promotion Candidates

- Promote the validated conclusion about cumulative recompute feasibility if the probe produces stable evidence.
