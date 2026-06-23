# Local ASR Model Inventory

Updated: 2026-06-23

This inventory records the model/cache files currently present on this Mac for LocalVoiceInput ASR evaluation. Sizes are from `du -sh` and are approximate on APFS.

## Current Product Direction

The current first integration candidate is `mlx-community__Qwen3-ASR-0.6B-8bit` through the validated local HTTP cumulative-wrapper service boundary. It is not native realtime streaming, but it has passed the current incremental UX gates and resource smoke checks.

MiMo-V2.5-ASR MLX remains useful as an offline quality reference. It is not the first floating-panel partial backend unless a chunked/session API is proven or a separate wrapper is validated.

## Model Cache

| Path | Size | Status | Keep Decision |
|---|---:|---|---|
| `.external/models/mlx-community__Qwen3-ASR-0.6B-8bit` | 964M | Primary Qwen3 MLX 0.6B 8-bit runtime used by the validated HTTP service gate. | Keep. First Swift-adapter candidate. |
| `.external/models/mlx-community__Qwen3-ASR-1.7B-8bit` | 2.3G | Larger Qwen3 MLX 8-bit candidate validated for local file-level comparison. | Keep for final-quality comparison and possible final-pass backend tests. |
| `.external/models/MiMo-V2.5-ASR-MLX` | 4.2G | Xiaomi/MiMo MLX ASR model; strongest file-level quality observed, but no validated session/partial API yet. | Keep as offline quality reference. |
| `.external/models/MiMo-Audio-Tokenizer` | 2.4G | Required tokenizer/audio sidecar for MiMo-V2.5-ASR MLX. | Keep with MiMo. |
| `.external/models/paraformer-online-small` | 280M | Existing FunASR online partial baseline. | Keep for current app/FunASR baseline. |
| `.external/models/paraformer-offline-small` | 280M | Existing FunASR offline final baseline. | Keep for current app/FunASR baseline. |
| `.external/models/fsmn-vad` | 3.9M | FunASR VAD cache. | Keep, although some Nano paths currently avoid VAD. |

Current `.external` total size after cleanup: about 10G.

## Local Runtime Repos

| Path | Size | Status |
|---|---:|---|
| `.external/repos/mlx-audio` | 14M | Active local MLX ASR runtime source used for Qwen3/MiMo/Nemotron probes. |
| `.external/repos/mlx-audio-main-src` | 16M | Source snapshot kept for comparison/debugging. |
| `.external/repos/mlx-audio-main.zip` | 6.7M | Archived source zip; cleanup candidate if source dirs are retained. |
| `.external/repos/FireRedASR2S` | 8.3M | Official FireRed inference code for prior local eval. |
| `.external/repos/MiMo-V2.5-ASR-MLX` | 1.3M | MiMo reference repo/source snapshot. |

## Models No Longer Planned For Mainline Integration

These are not planned for the first product integration path:

- Nemotron 3.5 ASR Streaming 0.6B MLX: name includes streaming, but the local runtime surface did not provide the needed session-style `start/push_pcm/partial/finish/cancel` contract, and local Chinese/technical-term quality was weak.
- GLM-ASR-Nano-2512: useful historical eval result, but not selected over Qwen3 MLX for the current incremental UX path.
- FireRedASR2-AED: locally runnable, but not selected for the near-term Mac MVP path.
- Fun-ASR-Nano-2512 4-bit MLX: useful comparison point, but not selected as the first partial/final backend.
- Original non-MLX Qwen3 caches: useful as official/reference caches, but the Apple Silicon path is the MLX 8-bit snapshots.

These caches have been removed from this Mac after their local eval evidence was preserved in `eval/asr_streaming/results/`. Re-download them only if old experiments need to be rerun.

## Cleanup Completed

On 2026-06-23, removed:

- Empty legacy model directory `.external/models/Qwen3-ASR-0.6B-8bit`.
- Unreferenced failed Qwen3 HTTP smoke result directories `qwen3-mlx-http-service-0.6b-smoke-20260623-145818` and `qwen3-mlx-http-service-0.6b-smoke-20260623-145900`.
- Empty or non-evidence smoke result directories for early failed/aborted probes.
- `.DS_Store` files and non-venv Python `__pycache__` directories.

Preserved all result directories referenced by SDD progress evidence, including the successful Qwen3 HTTP smoke, `long_120`, extended pass, and the earlier extended failure used to document the worker timing bug.

Later on 2026-06-23, removed additional non-mainline local caches:

- Redundant `.external/models/amd-transfer__*` model transfer copies.
- Original non-MLX Qwen3 caches `.external/models/Qwen3-ASR-0.6B` and `.external/models/Qwen3-ASR-1.7B`.
- Non-selected eval caches `.external/models/GLM-ASR-Nano-2512`, `.external/models/FireRedASR2-AED`, `.external/models/mlx-community__Fun-ASR-Nano-2512-4bit`, and `.external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit`.
- ModelScope cache `~/.cache/modelscope/hub/models/FunAudioLLM/Fun-ASR-Nano-2512`.
