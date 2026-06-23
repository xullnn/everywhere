# Decisions - Qwen3-ASR MLX Realtime Probe

## Confirmed Decisions

- D1: Treat `stream_transcribe(audio)` as file/token streaming unless the audio is accepted incrementally through a session API.
- D2: A model is realtime-gate eligible only if it exposes or is wrapped by a session-style `feed/step/close` contract.
- D3: Prefix-audio diagnostics can be used to measure whether early partial text is plausible, but they do not prove realtime session behavior.
- D4: The first runtime probe targets `qwen3-asr-0.6b-mlx-8bit`; 1.7B can be probed after the 0.6B surface is understood.
- D5: Both locally loaded Qwen3-ASR MLX 0.6B and 1.7B expose `generate`, `stream_transcribe`, and `stream_generate`, but neither exposes `create_streaming_session`.
- D6: Qwen3-ASR MLX is not realtime-gate eligible as currently loaded; any app-runtime path would require a custom session wrapper or upstream session API.

## Open Questions / Unresolved Choices

- Whether a custom cumulative-recompute service around Qwen3-ASR MLX would be fast enough for MVP partials.
- Whether Qwen3-ASR MLX can be modified to cache audio encoder state and expose a true session API.

## PMB Promotion Candidates

- Promote only the stable conclusion about Qwen3-ASR MLX realtime eligibility after runtime probe validation.
