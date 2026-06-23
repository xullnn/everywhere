# MLX ASR Candidate Comparison - 2026-06-22

## Scope

This comparison uses the same 10 local WAV cases from `eval/asr_streaming/cases.local.jsonl`.
All metrics below are Mac-local file-level results unless noted otherwise. AMD is treated only as a
download/cache host; product suitability is still judged from Mac-local runs. After the Mac-local
comparison, the required MLX candidate snapshots were also downloaded on AMD through `hf-mirror.com`,
synced back under `.external/models/amd-transfer__*`, verified for missing files, and smoke-tested
from the transferred directories where applicable.

## Metric Notes

- CER: 字符错误率，越低越好。主要看中文逐字准确率。
- WER: 词或 token 错误率，越低越好。这里中文近似按单字 token，连续英文/数字/符号按一个 token。
- RTF: 实时因子，等于评测耗时除以音频时长。小于 `1.0` 表示快于实时。
- 平均最终延迟: 文件送入模型后拿到 final 的平均耗时，单位 ms。它不是完整 App 录音链路延迟。

## Result Table

| Model | Status | CER | WER | RTF | Avg Final Latency | Main Finding |
|---|---:|---:|---:|---:|---:|---|
| Fun-ASR-Nano official file | 10/10 ok | 0.0758 | 0.2236 | 0.2080 | 3961.5 ms | Stronger than Paraformer baseline, but slower non-MLX file path. |
| Qwen3-ASR 0.6B official | 10/10 ok | 0.0470 | 0.1918 | 0.1264 | 3291.3 ms | Good accuracy, but slower transformers-style local path. |
| Qwen3-ASR 1.7B official | 10/10 ok | 0.0431 | 0.1760 | 0.1849 | 5064.6 ms | Best Qwen official accuracy, but slow in this harness. |
| MiMo-V2.5-ASR MLX | 10/10 ok | 0.0311 | 0.1613 | 0.1214 | 3216.5 ms | Best file-level accuracy, but currently offline-first and weaker as a realtime partial path. |
| Qwen3-ASR 0.6B MLX 8bit | 10/10 ok | 0.0510 | 0.1898 | 0.0212 | 531.6 ms | Fastest practical MLX candidate; slightly less accurate than 1.7B. |
| Qwen3-ASR 1.7B MLX 8bit | 10/10 ok | 0.0446 | 0.1740 | 0.0357 | 929.0 ms | Best current balance of accuracy, speed, size, and Apple Silicon runtime feasibility. |
| Nemotron 3.5 ASR 0.6B MLX 8bit | 9/10 ok, 1 no_text | 0.3090 | 0.2993 | 0.0177 | 480.5 ms | Very fast and has `stream_generate`, but quality is too weak for Chinese-first mixed English dictation. |
| Fun-ASR-Nano MLX 4bit | 10/10 ok | 0.3156 | 0.4378 | 0.0566 | 2425.4 ms | Short cases can work, but long-form reliability failed badly. |

## Recommendation

Primary next backend-integration spike: `mlx-community/Qwen3-ASR-1.7B-8bit`.

Reason:

- It is close to official Qwen3-ASR 1.7B accuracy on the local 10-case set.
- It is much faster than the official transformers-style local path in this harness.
- It fits comfortably on the target MacBook Pro M4 / 48GB.
- It already exposes file/token streaming through the MLX runtime, although microphone-session semantics still need a dedicated integration spike.

Fallback candidate: `mlx-community/Qwen3-ASR-0.6B-8bit`.

Reason:

- It is the fastest practical candidate tested so far.
- Accuracy is slightly weaker than 1.7B, but still much better than the failed Nemotron and Fun-ASR-Nano 4bit MLX conversions.
- It is a good low-latency fallback if the 1.7B streaming integration proves too complex or memory-heavy.

Accuracy-only reference: `MiMo-V2.5-ASR MLX`.

Reason:

- It has the best file-level CER/WER on the current local set.
- It should remain in the comparison as an offline-quality reference.
- It is not the first integration target because realtime partial/session behavior is not yet as favorable as Qwen3-ASR MLX.
- Its required companion `mlx-community/MiMo-Audio-Tokenizer` is present locally and was used by the MiMo adapter, but it is not a standalone ASR backend.

## AMD Transfer Proof

The strict AMD transfer proof covers these required MLX candidates:

- `mlx-community/Qwen3-ASR-0.6B-8bit`
- `mlx-community/Qwen3-ASR-1.7B-8bit`
- `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`
- `mlx-community/Fun-ASR-Nano-2512-4bit`
- `mlx-community/MiMo-Audio-Tokenizer`
- `mlx-community/MiMo-V2.5-ASR-MLX`

`MiMo-Audio-Tokenizer` is a required support artifact rather than a standalone ASR backend, so it was verified through the MiMo smoke run.

Not recommended as primary backend:

- `Nemotron 3.5 ASR 0.6B MLX 8bit`: speed and streaming API are attractive, but local Chinese/mixed-English quality is not acceptable.
- `Fun-ASR-Nano-2512 4bit MLX`: runtime works with a package-path workaround, but long-form output collapsed on critical cases.

## Runtime Caveats

- File-level results do not prove LocalVoiceInput microphone-session behavior.
- The next approved integration spike should test Qwen3-ASR MLX with timed PCM chunks, model reuse, cancellation, partial stability, final correction, and memory after repeated sessions.
- No Swift/macOS hotkey, focus, clipboard, paste, or floating-panel code was changed by this comparison.
