# Decisions - MLX ASR Model Download And Local Evaluation

## Confirmed decisions

- D1: Keep this work outside the LocalVoiceInput macOS app runtime until a backend is selected.
- D2: Use the AMD machine only as a download/cache transfer host because current Mac network conditions are unreliable.
- D3: Treat MacBook Pro M4 local smoke and full-run results as the authoritative product evidence.
- D4: Test MLX community variants before app integration because the previous runtime-feasibility comparison identified Qwen3-ASR MLX as the best next Apple Silicon spike.
- D5: Start with `mlx-community/Qwen3-ASR-0.6B-8bit` because it is the lowest-risk balance of size, likely quality, and Mac-native runtime feasibility.
- D6: AMD host `amd-easytier` is reachable and has enough disk. Detached Windows SSH background downloads are unreliable on this host, and direct `huggingface.co` times out from AMD, but a foreground PowerShell snapshot command through `hf-mirror.com` successfully downloaded `mlx-community/Qwen3-ASR-0.6B-8bit`; the snapshot was then synced back to the Mac and passed a Mac-local smoke test from the transferred directory.

## Open questions / unresolved choices

- Whether MLX Qwen3-ASR token streaming can operate as a practical microphone-session partial backend remains unproven.
- Whether Qwen3-ASR MLX token streaming can be adapted into a stable microphone-session backend with timely partials remains unproven.

## PMB promotion candidates

- Promote the final backend selection and reusable operational notes only after closeout validates the comparison.
