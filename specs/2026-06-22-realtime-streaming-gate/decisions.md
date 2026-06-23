# Decisions - Realtime ASR Streaming Gate

## Confirmed Decisions

- D1: Realtime backend ranking must be separate from file-level final transcription ranking.
- D2: A backend must emit partial text before simulated user stop to qualify as realtime for the current MVP.
- D3: Complete-audio `generate(...)` output, even if token-streamed after loading the whole file, is not sufficient evidence for realtime microphone input.
- D4: The first gate adapter is FunASR WebSocket 2pass because it already accepts PCM chunks and emits partial/final events.
- D5: Qwen3-ASR MLX remains a follow-up candidate until a session-style service can prove timed PCM chunk input and pre-stop partials.
- D6: MiMo-V2.5-ASR MLX remains a file-level quality reference unless a chunked or streaming API is proven.
- D7: The current Paraformer/FunASR baseline is confirmed true-streaming on the smoke case, but it fails the strict default latency gate because first partial and stop-to-final latency are both around 3 seconds.

## Open Questions / Unresolved Choices

- What threshold should the product ultimately enforce for first partial latency on long-form dictation: 1000 ms, 1500 ms, or a scenario-specific target?
- Whether final completeness should be a hard gate for long-form partial fallback or a separate final-quality warning.
- Whether Qwen3-ASR MLX can be adapted without recomputing from the entire accumulated audio buffer on every chunk.

## PMB Promotion Candidates

- Promote the realtime ASR service contract only after at least one non-baseline candidate passes the gate with stable local performance.
