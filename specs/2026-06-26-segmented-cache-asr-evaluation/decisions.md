# Decisions - Segmented Cache ASR Evaluation

## Confirmed Decisions

- D1: This feature evaluates segmented-cache behavior outside the macOS App runtime. It must not modify hotkeys, focus routing, paste, clipboard, floating panel, audio capture, or user-facing defaults.
- D2: The first implementation uses proportional transcript splitting only to make segment case files valid and reproducible. Segment-level CER/WER is not authoritative; aggregate source-case CER/WER is the quality signal.
- D3: The first pilot uses zero overlap by default to avoid duplicate text in naive aggregate analysis. Overlap remains supported as metadata and a later boundary-quality experiment.
- D4: Product thresholds will be chosen only after reviewing measured data; two minutes is not treated as a default.
- D5: The validated first-pass matrix supports moving toward a segmented-cache service design, but not directly changing the macOS App. The next runtime work should be a separate feature contract.

## Open Questions / Unresolved Choices

- O1: Final product segment thresholds remain open until more natural long-speech cases and repeated strategy sweeps are available.
- O2: Whether production should use recognized partial length, acoustic/VAD boundaries, punctuation, or a combination for soft text-budget decisions remains open.
- O3: Whether overlap requires alignment/deduplication logic before production use remains open.
- O4: Whether the default strategy should start near 30s/150 chars or 60s/250 chars remains open. The first matrix favored 30s/150 chars on stop-wait/backlog, but this may trade off context quality and segment count in less repetitive natural speech.

## PMB Promotion Candidates

- Promote only after validation: long dictation should use segmented local caching with hybrid budget controls instead of whole-session cumulative final recompute.
