# Decisions - Long-Dictation ASR Evaluation And Streaming-Route Validation

## Confirmed Decisions

- D1: Use public, license-trackable speech datasets with transcripts as the primary metric-bearing long audio source.
- D2: Use public talks/interviews only as experience-smoke material unless their license and transcript quality are good enough for metrics.
- D3: Do not require the user to manually record large long-dictation corpora before the automated public/local corpus path is exhausted.
- D4: Newly selected primary ASR candidates should be recent: released or materially updated within the past year. Older routes may remain as baselines/reference-only.
- D5: The immediate Qwen3 objective is to measure the current cumulative wrapper limit and verify whether a better stateful/streaming MLX surface exists.
- D6: Stable-prefix plus mutable-tail is a promising architecture direction, but implementation belongs in a later feature after the measurement/probe evidence is available.
- D7: Synthetic repeated audio is allowed only for compute/backlog stress. It must not be used as evidence that a route handles natural long speech UX.
- D8: `mlx-qwen3-asr` source/API probing is enough for this feature; model-loaded timed PCM smoke is a follow-up because it needs a dedicated adapter and validation contract.

## Open Questions / Unresolved Choices

- O1: Which exact public dataset slices and talk/interview clips should become the first runnable long-corpus set.
- O2: Whether `mlx-qwen3-asr` is acceptable as a dependency if its local timed PCM streaming claims validate.
- O3: Whether final refinement may rewrite committed stable segments in long draft mode.
- O4: Product thresholds for acceptable long-draft partial latency, final latency, and text churn.

## PMB Promotion Candidates

- Long corpus policy: metric-bearing cases require trusted transcripts; public media without transcript is experience-smoke only.
- Qwen3 cumulative wrapper long-duration limits after local benchmark evidence exists.
- Verified `mlx-qwen3-asr` streaming surface if local proof succeeds.
