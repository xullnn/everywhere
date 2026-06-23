# Remote Model Acquisition

This note records the repeatable path for using the current AMD Windows machine as a large-model download cache while keeping Mac-local ASR evaluation authoritative.

## AMD host

- Preferred SSH alias: `amd-local`
- Fallback SSH alias: `amd-easytier`
- Observed host: `DESKTOP-44OENPE`
- Observed user: `desktop-44oenpe\mac_xll`
- Preferred remote cache root: `E:\LocalVoiceInputModels\hf`

The AMD machine is a download/cache transfer host only. Runtime quality and product suitability are measured on the target Mac.

## Download a Hugging Face snapshot on AMD

Copy the PowerShell helper to AMD:

```bash
ssh amd-easytier "cmd /c if not exist E:\LocalVoiceInputModels\bin mkdir E:\LocalVoiceInputModels\bin"
scp eval/asr_streaming/download_hf_snapshot_windows.ps1 \
    eval/asr_streaming/start_hf_download_windows.ps1 \
    eval/asr_streaming/show_hf_download_status_windows.ps1 \
    amd-easytier:'E:/LocalVoiceInputModels/bin/'
```

Start a resumable download:

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit -BaseUrl https://hf-mirror.com -DestinationRoot E:\LocalVoiceInputModels\hf'
```

For long downloads, first prefer a foreground SSH session. The detached PowerShell helper is
available, but Windows OpenSSH sessions may clean up or fail to start background children on this
host, so treat the status command as the source of truth.

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit -BaseUrl https://hf-mirror.com'
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\start_hf_download_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit -BaseUrl https://hf-mirror.com'
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\show_hf_download_status_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit'
```

## Sync to Mac

The AMD host currently does not expose `rsync`. Use `scp` first, and use `sftp reget` manually only if a large transfer is interrupted.

```bash
mkdir -p .external/models/Qwen3-ASR-0.6B-8bit
scp -r amd-easytier:'E:/LocalVoiceInputModels/hf/mlx-community__Qwen3-ASR-0.6B-8bit/*' \
  .external/models/Qwen3-ASR-0.6B-8bit/
```

After sync, verify local file count and size before running inference.

## Validated AMD transfer

Validated on 2026-06-22 with `mlx-community/Qwen3-ASR-0.6B-8bit`:

- AMD direct `https://huggingface.co` API request timed out.
- AMD `https://hf-mirror.com` API request succeeded.
- The foreground PowerShell snapshot command downloaded a complete Qwen3-ASR 0.6B 8-bit MLX snapshot under `E:\LocalVoiceInputModels\hf\mlx-community__Qwen3-ASR-0.6B-8bit`.
- Remote integrity check: Hugging Face API expected `11` files, AMD cache had `11`, missing `0`, total bytes `1,010,776,472`.
- Sync command:

```bash
mkdir -p .external/models/amd-transfer__Qwen3-ASR-0.6B-8bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__Qwen3-ASR-0.6B-8bit/. \
  .external/models/amd-transfer__Qwen3-ASR-0.6B-8bit/
```

- Mac integrity check: expected `11`, existing `11`, missing `0`, total bytes `1,010,776,472`; `model.safetensors` was `1,006,229,426` bytes.
- Mac smoke result from the transferred directory: `qwen3-asr-0.6b-mlx-amd-transfer-smoke-20260622`, status `ok`, CER `0.1053`, WER `0.1053`, RTF `0.0286`.

Also validated on 2026-06-22 with `mlx-community/Qwen3-ASR-1.7B-8bit`:

- The first attempt reached a partial `model.safetensors` and was resumable.
- The Windows helper was updated to add `curl.exe --silent --show-error` so long foreground downloads do not flood the SSH terminal; this does not change resume/download semantics.
- The resumed foreground PowerShell snapshot command completed under `E:\LocalVoiceInputModels\hf\mlx-community__Qwen3-ASR-1.7B-8bit`.
- Remote integrity check: Hugging Face API expected `11` files, AMD cache had `11`, missing `0`, total bytes `2,467,861,660`; `model.safetensors` was `2,463,307,541` bytes.
- Sync command:

```bash
mkdir -p .external/models/amd-transfer__Qwen3-ASR-1.7B-8bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__Qwen3-ASR-1.7B-8bit/. \
  .external/models/amd-transfer__Qwen3-ASR-1.7B-8bit/
```

- Mac integrity check: expected `11`, existing `11`, missing `0`, total bytes `2,467,861,660`; `model.safetensors` was `2,463,307,541` bytes.
- Mac smoke result from the transferred directory: `qwen3-asr-1.7b-mlx-amd-transfer-smoke-20260622`, status `ok`, CER `0.1053`, WER `0.1053`, RTF `0.0474`.

Also validated on 2026-06-22 with `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`:

- The foreground PowerShell snapshot command completed under `E:\LocalVoiceInputModels\hf\mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit`.
- Remote integrity check: Hugging Face API expected `6` files, AMD cache had `6`, missing `0`, total bytes `756,249,995`; `model.safetensors` was `755,598,923` bytes.
- Sync command:

```bash
mkdir -p .external/models/amd-transfer__nemotron-3.5-asr-streaming-0.6b-8bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit/. \
  .external/models/amd-transfer__nemotron-3.5-asr-streaming-0.6b-8bit/
```

- Mac integrity check: expected `6`, existing `6`, missing `0`, total bytes `756,249,995`; `model.safetensors` was `755,598,923` bytes.
- Mac smoke result from the transferred directory: `nemotron-3.5-asr-streaming-0.6b-mlx-amd-transfer-smoke-20260622`, status `ok`, CER `0.1053`, WER `0.1053`, RTF `0.0209`.

Also validated on 2026-06-22 with `mlx-community/Fun-ASR-Nano-2512-4bit`:

- The foreground PowerShell snapshot command completed under `E:\LocalVoiceInputModels\hf\mlx-community__Fun-ASR-Nano-2512-4bit`.
- Remote integrity check: Hugging Face API expected `8` files, AMD cache had `8`, missing `0`, total bytes `1,335,672,632`; `model.safetensors` was `1,319,780,726` bytes.
- Sync command:

```bash
mkdir -p .external/models/amd-transfer__Fun-ASR-Nano-2512-4bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__Fun-ASR-Nano-2512-4bit/. \
  .external/models/amd-transfer__Fun-ASR-Nano-2512-4bit/
```

- Mac integrity check: expected `8`, existing `8`, missing `0`, total bytes `1,335,672,632`; `model.safetensors` was `1,319,780,726` bytes.
- Mac smoke result from the transferred directory: `fun-asr-nano-2512-mlx-4bit-amd-transfer-smoke-20260622`, status `ok`, CER `0.1053`, WER `0.1053`, RTF `0.0485`.

Also validated on 2026-06-22 with `mlx-community/MiMo-Audio-Tokenizer`:

- The foreground PowerShell snapshot command completed under `E:\LocalVoiceInputModels\hf\mlx-community__MiMo-Audio-Tokenizer`.
- The first large-file attempt failed with curl exit `18`; the second run resumed successfully from the partial file.
- Remote integrity check: Hugging Face API expected `7` files, AMD cache had `7`, missing `0`, total bytes `2,575,685,063`; `model.safetensors` was `2,575,648,345` bytes.
- Sync command:

```bash
mkdir -p .external/models/amd-transfer__MiMo-Audio-Tokenizer
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__MiMo-Audio-Tokenizer/. \
  .external/models/amd-transfer__MiMo-Audio-Tokenizer/
```

- Mac integrity check: expected `7`, existing `7`, missing `0`, total bytes `2,575,685,063`; `model.safetensors` was `2,575,648,345` bytes.

Also validated on 2026-06-22 with `mlx-community/MiMo-V2.5-ASR-MLX`:

- The foreground PowerShell snapshot command completed under `E:\LocalVoiceInputModels\hf\mlx-community__MiMo-V2.5-ASR-MLX`.
- The first large-file attempt failed with curl exit `18`; the second run resumed successfully from the partial file.
- Remote integrity check: Hugging Face API expected `15` files, AMD cache had `15`, missing `0`, total bytes `4,527,589,096`; `model.safetensors` was `4,511,552,749` bytes.
- Sync command:

```bash
mkdir -p .external/models/amd-transfer__MiMo-V2.5-ASR-MLX
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__MiMo-V2.5-ASR-MLX/. \
  .external/models/amd-transfer__MiMo-V2.5-ASR-MLX/
```

- Mac integrity check: expected `15`, existing `15`, missing `0`, total bytes `4,527,589,096`; `model.safetensors` was `4,511,552,749` bytes.
- Mac smoke result using both AMD-transferred MiMo directories: `mimo-v25-asr-mlx-amd-transfer-smoke-20260622`, status `ok`, CER `0.0000`, WER `0.0000`, RTF `0.2945`.

## Mac-local fallback

If the AMD host cannot keep a background job alive or is materially slower than the Mac, use the same snapshot strategy on the Mac:

```bash
bash eval/asr_streaming/download_hf_snapshot.sh \
  --repo mlx-community/Qwen3-ASR-0.6B-8bit \
  --base-url https://huggingface.co \
  --dest-root .external/models
```

This does not change the final evaluation standard: inference and model suitability are still measured on the Mac.
