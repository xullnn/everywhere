# Requirements - Qwen3-ASR MLX HTTP Service Boundary

## Problem

Qwen3-ASR MLX 0.6B cumulative recompute has passed in-process service prototype checks, but LocalVoiceInput cannot treat it as an app backend candidate until the same behavior works across a real local process/transport boundary. The canonical `incremental_ux_gate.py` now supports `http-json`; this feature uses that seam to expose the Qwen3 cumulative wrapper as a localhost service.

## Scope

### IN

- Add a local HTTP service process for the existing Qwen3-ASR MLX cumulative recompute wrapper.
- Support the canonical service actions: `start`, `chunk`, `finish`, and `cancel`.
- Load the Qwen3-ASR MLX model once at service startup for real runs.
- Provide a fake-backend mode for lightweight CI/self-test without model weights.
- Return only normalized backend events that `incremental_ux_gate.py --adapter http-json` can consume.
- Preserve session ownership so the service uses the gate-provided session token.
- Keep all work isolated to eval harness, scripts, and SDD docs.

### OUT

- No Swift App runtime integration.
- No macOS hotkey, focus, paste, clipboard, floating-panel, or AVAudioEngine changes.
- No InputMethodKit migration.
- No cloud ASR, remote inference, or audio/text upload.
- No final backend role decision in this feature.
- No MiMo, Qwen3 1.7B, FunASR, GLM, FireRed, or Nemotron service work.

## Requirements

- R1: The service must implement localhost HTTP JSON endpoints compatible with `incremental_ux_gate.py --adapter http-json`.
- R2: The service must accept client-provided `session_id` and `session_token` and use that token in returned partial/final events.
- R3: `/chunk` must decode 16 kHz mono int16 PCM from base64 JSON and feed it to the cumulative recompute wrapper.
- R4: `/finish` must return final text only after the gate sends finish.
- R5: `/cancel` must prevent later accepted partial/final output for that session.
- R6: The service must include a fake-backend mode that proves the HTTP process boundary without loading MLX/model weights.
- R7: The real Qwen3 mode must use local model paths only and must not download or upload data during gate runs.
- R8: The feature must record whether real-model smoke was run, passed, skipped, or blocked with concrete reason.
- R9: Existing fake and in-process gate tests must continue to pass.

## Constraints

- Use Python standard-library HTTP server for the first process boundary.
- Reuse `qwen3_mlx_cumulative_service.py` model loading and wrapper logic where possible.
- Do not classify cumulative recompute as native realtime streaming.
- Do not mark the roadmap complete from this feature alone.

## Dependencies

- `2026-06-23-incremental-ux-real-backend-adapters`
- `2026-06-22-qwen3-mlx-cumulative-service-prototype`
- `2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
