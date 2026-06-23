# Requirements - Qwen3-ASR MLX Cumulative Service Prototype

## Problem

Qwen3-ASR MLX does not expose a native microphone session API, but cumulative recompute looks fast enough to justify a local wrapper prototype. Before touching the Swift app, the project needs an independent service-level simulation that proves the session contract, timing semantics, cancellation behavior, and stale-result isolation expected by LocalVoiceInput.

## Scope

### IN

- Add an independent Python probe that emulates a local ASR service contract:
  - `start(session_id, options)`
  - `push_pcm(session_id, pcm16k_mono)`
  - `partial(session_id, text, revision, is_final=false)`
  - `finish(session_id)`
  - `final(session_id, text, is_final=true)`
  - `cancel(session_id)`
- Feed local 16 kHz mono int16 WAV cases as timed PCM chunks.
- Run cumulative prefix recompute on Qwen3-ASR MLX using one loaded model process.
- Record service events, chunk timing, ignored stale events, partial cadence, first usable partial latency, final latency, final CER/WER, and Chinese metric explanations.
- Provide a self-test path that does not require MLX or model weights and covers stale events, final-after-stop ordering, and cancel behavior.

### OUT

- Do not integrate the prototype into `LocalVoiceInputMac`.
- Do not modify Swift hotkeys, focus detection, clipboard, paste, floating panel, or AVAudioEngine code.
- Do not claim cumulative recompute is native realtime streaming.
- Do not introduce cloud ASR, remote uploads, LLM correction, or auto-send behavior.

## Requirements

- R1: The prototype must preserve session ownership so old partial/final jobs cannot affect a new session.
- R2: `cancel(session_id)` must emit no final text and no post-cancel partial/final output for that session.
- R3: `finish(session_id)` must produce final output after simulated user stop and ignore late partials that arrive afterward.
- R4: Service summaries must explicitly distinguish `service_gate_passed` from `native_realtime_gate_eligible`.
- R5: Runtime probes must keep all outputs under `eval/asr_streaming/results/`.
- R6: Default validation must remain lightweight and not load heavy MLX model weights.

## Constraints

- Use only local model snapshots under `.external/models/`.
- Use local `mlx-audio` source through `PYTHONPATH`.
- Keep the script independent from macOS app runtime.
- Use existing ASR harness helpers for WAV loading, metrics, model metadata, and JSON output.

## Dependencies

- `specs/2026-06-22-realtime-streaming-gate`
- `specs/2026-06-22-qwen3-mlx-realtime-probe`
- `specs/2026-06-22-qwen3-mlx-cumulative-recompute-probe`
- `specs/2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
