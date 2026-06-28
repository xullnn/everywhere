# Decisions - Segment Budget ASR Evaluation

## Confirmed Decisions

- D1: Treat two minutes as an example threshold, not a product decision.
- D2: Test both audio-duration pressure and text/content-length pressure before proposing segment boundaries.
- D3: Use synthetic silence padding and repetition only as compute-isolation evidence, not as natural speech UX evidence.
- D4: Keep this feature as measurement-only; App runtime segmentation changes need a separate implementation feature.
- D5: Pilot evidence shows audio duration matters even when recognized text is unchanged, and text/content amount adds additional cost beyond silence padding.
- D6: The 131.669s / 488 normalized-character repeated-content stress case returned only 366 normalized characters and CER/WER 0.2561, so a fixed two-minute final-recompute segment is not safe to adopt without more evidence and guardrails.

## Open Questions / Unresolved Choices

- O1: Final segment thresholds for product use remain open until repeat-run evidence and natural long-speech cases are available.
- O2: Whether future segmentation should commit text only at punctuation/silence boundaries, a hard resource budget, or both.
- O3: Whether the 4x repeated-content truncation is caused by model/generation limits, repeated synthetic content behavior, output token limits, or a broader long-audio reliability boundary.

## PMB Promotion Candidates

- Promote only the validated high-level conclusion about segment-boundary policy after pilot evidence is reviewed.
