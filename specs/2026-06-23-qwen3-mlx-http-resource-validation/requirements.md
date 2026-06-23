# Requirements - Qwen3-ASR MLX HTTP Resource And Extended Gate Validation

## Problem

The Qwen3-ASR 0.6B MLX HTTP service boundary passed smoke and `long_120_001`, but Swift integration still needs more evidence about longer existing recordings and local process resource behavior. This feature extends validation without asking the user to record new audio and without touching the macOS app runtime.

## Scope

### IN

- Run the existing Qwen3-ASR 0.6B MLX HTTP service through longer existing eval cases.
- Collect process resource samples for RSS and CPU while the HTTP service runs.
- Keep output as structured files under `eval/asr_streaming/results/`.
- Add repeatable scripts/case lists so the run can be repeated without manual setup.
- Record whether extended gates pass, fail, or expose performance risks.

### OUT

- No Swift App runtime integration.
- No changes to hotkeys, focus detection, paste, clipboard, floating panel, AVAudioEngine, or existing app safety behavior.
- No new audio recording requirement.
- No cloud ASR, remote inference, or upload.
- No final production service manager or LaunchAgent work.
- No hard product decision to replace FunASR in the app.

## Requirements

- R1: Provide a long-case JSONL file covering currently available longer recordings: `long_200_001`, `long_400_001`, and `long_code_switch_001`.
- R2: Provide a one-command runner that starts the local Qwen3 MLX HTTP service, waits for `/health`, runs `incremental_ux_gate.py --adapter http-json`, samples service RSS/CPU, and writes a resource summary.
- R3: The runner must use local model/runtime paths only and must not download or upload audio/text.
- R4: The runner must clean up service and monitor processes even when the gate fails.
- R5: Resource output must include peak RSS, mean RSS, peak CPU, mean CPU, sample count, and service/gate result paths.
- R6: Existing eval harness validation must continue to pass.
- R7: Results must keep metric explanations with Chinese descriptions through the existing gate summary.

## Constraints

- Use standard library and shell tooling where practical; do not introduce a new Python dependency only for resource sampling.
- Keep Qwen3 MLX inference on the owning service thread.
- Treat RTF from realtime-paced gate as wall-clock end-to-end behavior, not pure compute throughput.

## Dependencies

- `2026-06-23-qwen3-mlx-http-service-boundary`
- `2026-06-22-incremental-ux-asr-gate`
- `2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
