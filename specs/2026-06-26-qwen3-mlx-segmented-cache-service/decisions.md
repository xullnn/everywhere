# Decisions - Qwen3-ASR MLX Segmented Cache Service Prototype

## Accepted

- Use a separate prototype file instead of modifying the cumulative service in place.
- Keep Swift App integration out of this feature.
- Keep user-visible events limited to `partial` and `final`; segment-level events are diagnostic.
- Default merge policy is zero-overlap concatenation.
- Default runtime policy uses hard segment duration plus optional soft partial-text character budget.

## Open Questions

- What production default should be used for `max_segment_sec`, `min_segment_sec`, and `soft_text_chars` after more natural long-dictation data?
- Should production add VAD/silence and punctuation-aware segment boundaries before Swift integration?
- Should committed segments be written into the target app incrementally in long draft mode, or should final insertion still happen only at user stop?
- What crash-recovery UX should expose cached audio/text to the user?

## Rejected For This Feature

- Whole-session final recompute for very long dictation.
- Cloud fallback.
- LLM correction as a required part of ASR service correctness.
- Changing current App defaults before service-contract validation.
