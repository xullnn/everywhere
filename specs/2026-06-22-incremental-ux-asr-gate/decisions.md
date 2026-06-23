# Decisions - Incremental UX ASR Gate

## Confirmed Decisions

- D1: Treat the product target as perceived realtime / incremental UX, not strict word-by-word native streaming.
- D2: Build a backend-neutral gate before choosing a new app ASR backend.
- D3: Keep file-level final quality, native streaming capability, and cumulative wrapper readiness as separate evidence categories.
- D4: Do not wire Qwen3-ASR MLX, MiMo, or any new backend into the Swift app during this feature.
- D5: Do not default-enable cloud ASR, LLM correction, or any audio/text upload.

## Open Questions / Unresolved Choices

- Q1: Which backend should be the first real adapter after the fake gate: Qwen3-ASR MLX local service, FunASR compatibility adapter, or MiMo final-only/coarse adapter?
- Q2: What final latency threshold is acceptable for long-draft mode versus short push-to-talk mode?
- Q3: How much partial rewrite is acceptable before users perceive the floating panel as unstable?

## Notes

- The default near-term recommendation is Qwen3-ASR MLX 0.6B behind a real local service boundary, then MiMo-V2.5-ASR MLX as a final-only/coarse-incremental follow-up probe.
