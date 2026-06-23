# ASR Streaming Evaluation Harness

This harness tests ASR backends with WAV files that simulate realtime microphone streaming. It is independent from the macOS app, hotkeys, focus detection, clipboard, paste engine, and floating panel.

## Case format

Cases are JSONL. Each line must contain:

```json
{"id":"zh_short_001","audio":"audio/zh_short_001.wav","text":"我想要做一个本地离线的中文语音输入工具。","lang":"zh","scenario":"short_dictation"}
```

Audio for runnable cases must be 16 kHz, mono, signed 16-bit PCM WAV. The first pass intentionally does not resample audio so that evaluation inputs are explicit and reproducible.

## Commands

Start the guided recording tool:

```bash
bash scripts/record_asr_cases.sh
```

The tool creates `eval/asr_streaming/cases.local.jsonl` from the first 10 template cases when missing, displays one text at a time, and records directly to `eval/asr_streaming/audio/<case_id>.wav`.

List microphone devices:

```bash
bash scripts/record_asr_cases.sh --list-devices
```

Dry-run setup without recording:

```bash
bash scripts/record_asr_cases.sh --dry-run
```

List model candidates:

```bash
python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json
```

Validate the example schema without requiring audio files:

```bash
python3 eval/asr_streaming/run_eval.py validate-cases \
  --cases eval/asr_streaming/cases.example.jsonl \
  --allow-missing-audio
```

Run against the current FunASR WebSocket server:

```bash
bash scripts/run_funasr_python_server.sh
python3 eval/asr_streaming/run_eval.py run \
  --adapter funasr-ws \
  --model-id paraformer-current-funasr-ws \
  --cases eval/asr_streaming/cases.local.jsonl \
  --ws-url ws://127.0.0.1:10095 \
  --out-dir eval/asr_streaming/results
```

Run the stricter realtime streaming gate against the current FunASR WebSocket server:

```bash
bash scripts/run_funasr_python_server.sh
python3 eval/asr_streaming/realtime_gate.py run \
  --adapter funasr-ws \
  --model-id paraformer-current-funasr-ws \
  --cases eval/asr_streaming/cases.local.jsonl \
  --ws-url ws://127.0.0.1:10095 \
  --chunk-ms 100 \
  --out-dir eval/asr_streaming/results/realtime-gate-funasr
```

Use `realtime_gate.py` when deciding whether a backend can power the MVP floating-panel partial experience. It requires partial text before simulated user stop, flags late partial after final, and records chunk traces in `chunks.jsonl`. Use `--warn-only` for exploratory runs where you want summaries even if a case fails the gate without returning a failing shell exit code.

File-level adapters such as `qwen3-asr-local`, `mimo-asr-mlx-local`, and `mlx-stt-local` are still useful for final transcription quality, but they are not realtime backend evidence unless they pass an equivalent push-PCM gate.

Run the backend-neutral incremental UX gate self-test:

```bash
python3 eval/asr_streaming/incremental_ux_gate.py self-test
```

Run a fake incremental backend through the gate:

```bash
python3 eval/asr_streaming/incremental_ux_gate.py run \
  --adapter fake-valid \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/incremental-ux-gate-fake-smoke \
  --no-realtime
```

`incremental_ux_gate.py` is the shared contract for perceived-realtime backends. It validates `start`, timed `push_pcm`, pre-stop `partial`, post-stop `final`, `cancel`, stale-session rejection, late-partial rejection, chunk traces, and Chinese metric explanations. The current adapters are fake protocol adapters only; real Qwen3-ASR MLX, MiMo, or other backend adapters should be added after the service boundary is implemented. Use `--no-realtime` only for fast protocol diagnostics. Product latency evidence should use realtime pacing.

Probe whether Qwen3-ASR MLX has a true realtime session API:

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_realtime_probe.py probe \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --language Chinese \
  --run-prefix-smoke \
  --out-dir eval/asr_streaming/results/qwen3-mlx-realtime-probe-0.6b-smoke
```

This probe is deliberately stricter than checking whether `stream_transcribe(...)` returns token chunks. A model is realtime-gate eligible only if it exposes a session-style API, or an equivalent local service contract, that accepts incremental PCM chunks.

Probe whether Qwen3-ASR MLX cumulative recompute is worth a future local service wrapper:

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_cumulative_probe.py run \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.local.jsonl \
  --case-id long_120_001 \
  --language Chinese \
  --max-prefixes 8 \
  --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-long120
```

This cumulative probe periodically reruns the model on 1s, 2s, 3s, ... accumulated audio prefixes and treats those outputs as simulated partials. It records prefix latency, queued serial-worker latency, serial recompute RTF, prefix rewrite rate, final CER/WER, and always marks `native_realtime_gate_eligible=false`. A good cumulative result means “worth prototyping a local wrapper,” not “ready to wire into the app.”

Prototype the cumulative recompute service contract:

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python \
  eval/asr_streaming/qwen3_mlx_cumulative_service.py run \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --cases eval/asr_streaming/cases.local.jsonl \
  --case-id long_120_001 \
  --language Chinese \
  --max-prefixes 8 \
  --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-long120
```

This service probe validates the wrapper contract independently from the macOS app: `start`, timed `push_pcm`, `partial`, `finish`, `final`, and `cancel`. Its self-test covers old session event rejection, late partial rejection after final, and cancel producing no final. Runtime summaries include `service_gate_passed` and keep `native_realtime_gate_eligible=false`.

Run a local file-level Fun-ASR-Nano candidate smoke test:

```bash
bash scripts/run_fun_asr_nano_smoke.sh
```

Check the smoke command without downloading or loading the model:

```bash
DRY_RUN=1 bash scripts/run_fun_asr_nano_smoke.sh
```

Or run the adapter directly:

```bash
python3 eval/asr_streaming/run_eval.py run \
  --adapter funasr-nano-local \
  --model-id fun-asr-nano-2512 \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/fun-asr-nano-local
```

The `funasr-nano-local` adapter is a file-level quality/runtime screen. It records a final result for each WAV, but it does not provide realtime partials. Use it to decide whether the model is worth deeper streaming-service work.

For the current FunASR 1.3.1 local path, the `funasr-nano-local` adapter defaults to no VAD. The FunASR VAD wrapper reaches inference, but raises `KeyError(0)` when combining VAD segments with the Nano result structure. Use explicit `--funasr-vad-model fsmn-vad` only when validating a newer runtime that fixes that behavior.

Prepare and run a local file-level Qwen3-ASR 0.6B candidate smoke test:

```bash
bash scripts/setup_qwen3_asr_venv.sh
bash scripts/download_qwen3_asr.sh
bash scripts/run_qwen3_asr_smoke.sh
```

Check the smoke command without downloading or loading the model:

```bash
DRY_RUN=1 bash scripts/run_qwen3_asr_smoke.sh
```

Or run the adapter directly:

```bash
python3 eval/asr_streaming/run_eval.py run \
  --adapter qwen3-asr-local \
  --model-id qwen3-asr-0.6b \
  --qwen3-model .external/models/Qwen3-ASR-0.6B \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-local
```

The `qwen3-asr-local` adapter uses the official `qwen-asr` transformers backend as a file-level quality/runtime screen. It records a final result for each WAV, but it does not provide realtime partials. Official Qwen3-ASR streaming support is vLLM-based and remains a separate follow-up.

Run a local file-level MiMo-V2.5-ASR MLX candidate evaluation:

```bash
.venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mimo-asr-mlx-local \
  --model-id mimo-v2.5-asr \
  --mimo-model .external/models/MiMo-V2.5-ASR-MLX \
  --mimo-audio-tokenizer-dir .external/models/MiMo-Audio-Tokenizer \
  --mimo-language zh \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/mimo-v25-asr-mlx-local
```

The `mimo-asr-mlx-local` adapter uses the Apple MLX `mlx-audio` path as a file-level quality/runtime screen. It records a final result for each WAV, but it does not provide realtime partials. Treat first-run cold-load time separately from per-case inference timing.

## Output

For each run the harness writes:

- `events.jsonl`: every backend event with local receive timestamp and raw payload.
- `summary.json`: per-case metrics and final text.

For each realtime gate run, the harness also writes:

- `chunks.jsonl`: every PCM chunk sent to the backend with local send timing and audio time span.
- realtime gate fields in `summary.json`: `realtime_gate_passed`, `gate_fail_reasons`, `partial_before_stop_count`, `final_after_stop_count`, `partial_cadence_ms`, `final_coverage_ratio`, and related thresholds.

For each incremental UX gate run, the harness writes:

- `chunks.jsonl`: every PCM chunk offered to the backend with local send timing and audio time span.
- `events.jsonl`: accepted and ignored session events, including stale-session and cancel-related ignores.
- incremental UX gate fields in `summary.json`: `incremental_ux_gate_passed`, `gate_fail_reasons`, `first_partial_latency_ms`, `partial_cadence_ms`, `final_latency_ms`, `partial_rewrite_rate`, `accepted_output_after_cancel`, `ignored_stale_event_count`, and `native_realtime_gate_eligible`.

The summary includes CER, WER, first partial latency, final latency, realtime factor, event counts, and status.

Every aggregate and per-case `summary.json` also includes:

- `model_info`: model supplier, Chinese supplier name, parameter scale, release date, runtime, adapter, and local validation status from `model_registry.json`.
- `metric_explanations_zh`: Chinese explanations for CER, WER, latency, RTF, event counts, final selection strategy, and incomplete-final flags.

Key metric meanings:

- `cer`: 字符错误率，越低越好。主要用于中文转写准确率。
- `wer`: 词或 token 错误率，越低越好。中英混合和技术词场景要重点看。
- `first_partial_ms`: 首个实时转写返回延迟，影响浮窗是否及时显示。
- `final_latency_ms`: 停止录音后等待最终结果的延迟。
- `rtf`: 实时因子，`< 1` 快于实时，`> 1` 慢于实时。
- `suspect_incomplete_final`: true 表示后端 final/offline 结果疑似不完整，不能直接当整段最终输出。
- `realtime_gate_passed`: 实时输入门槛是否通过。必须在模拟用户停止前收到 partial，并在停止后得到稳定 final/offline 事件。
- `incremental_ux_gate_passed`: 用户感知实时门槛是否通过。必须在用户停止前出现 accepted partial，停止后出现 accepted final，并且没有 cancel 泄漏、旧 session 污染或 final 后 late partial。
- `gate_fail_reasons`: 未通过实时门槛的具体原因，例如没有 pre-stop partial、首个 partial 太慢、late partial 出现在 final 之后等。
- `final_after_stop_count`: 模拟用户停止后收到的 final/offline 事件数量；中途 offline segment 不等于整段会话最终结果。
- `partial_cadence_ms`: partial 平均到达间隔，越低说明浮窗更新越密。
- `final_coverage_ratio`: 最终文本长度相对标准答案的覆盖率，过低说明 final 疑似不完整。

When adding a candidate backend, first add or update its `model_registry.json` entry with at least:

- `vendor` / `vendor_zh`
- `parameter_scale` / `parameter_scale_zh`
- `release_date` / `release_date_zh`
- `release_date_precision`
- `runtime`
- `adapter`
- `local_validation`
