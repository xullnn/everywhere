# Decisions - Nemotron MLX Realtime Surface Probe

## Confirmed Decisions

- D1: Treat Nemotron `stream_generate(audio)` as cache-aware file/token streaming unless the runtime exposes incremental PCM session methods.
- D2: Do not edit vendored `mlx-audio` source just to make the loader recognize `nemotron_asr`; use a narrow in-process loader shim in the evaluation script.
- D3: The local Nemotron MLX snapshot is not realtime-gate eligible because it does not expose `create_streaming_session`, `feed`, `step`, or `close`.

## Open Questions / Unresolved Choices

- Whether a different runtime for upstream NVIDIA Nemotron exposes a true microphone-session API suitable for Apple Silicon.
- Whether the weak local Chinese/technical-term quality makes further Nemotron integration work low priority even if a session runtime appears later.

## PMB Promotion Candidates

- Promote the validated no-session-API conclusion for local Nemotron MLX.
