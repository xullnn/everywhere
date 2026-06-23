# Requirements - Qwen3-ASR MLX Cumulative Recompute Probe

## Problem

The Qwen3-ASR MLX runtime exposes token streaming over an already provided audio buffer, but it does not expose a persistent microphone session API. Before considering a custom LocalVoiceInput service wrapper, the project needs measured evidence for whether periodically rerunning Qwen3-ASR MLX on accumulated prefix audio can produce usable partial text with acceptable latency and stability.

## Scope

### IN

- Add an independent cumulative-prefix probe for Qwen3-ASR MLX.
- Feed fixed local WAV cases as accumulated prefixes such as 1s, 2s, 3s, then run one full final pass.
- Record prefix wall time, prefix RTF, estimated first visible partial timing, queued serial-worker latency, prefix rewrite rate, final CER/WER, and Chinese metric explanations.
- Clearly mark cumulative recompute as not equivalent to native realtime gate success.

### OUT

- Do not integrate Qwen3-ASR MLX into the Swift macOS app.
- Do not change hotkeys, focus detection, clipboard, paste, floating panel, or ASR session code.
- Do not claim cumulative recompute is native realtime streaming.
- Do not introduce cloud uploads or remote ASR dependencies.

## Requirements

- R1: The probe must run without changing the existing file-level ASR harness contracts.
- R2: The probe must support case filtering so short smoke and long-form diagnostics can be run separately.
- R3: The output must include machine-readable failure reasons for wrapper viability.
- R4: The output must always set native realtime gate eligibility to false for cumulative recompute.
- R5: The script must provide a self-test path that does not require loading MLX or model weights.

## Constraints

- Use local `.external/models/` snapshots and local `.external/repos/mlx-audio` source.
- Keep generated outputs under `eval/asr_streaming/results/`.
- Keep validation independent from the macOS app runtime.

## Dependencies

- `specs/2026-06-22-realtime-streaming-gate`
- `specs/2026-06-22-qwen3-mlx-realtime-probe`
- `specs/2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
