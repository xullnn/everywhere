# ASR Runtime Feasibility Comparison

Date: 2026-06-22

## Scope

This note compares the currently strongest local ASR candidates for use as a
LocalVoiceInput backend. It separates file-level transcription quality from the
runtime behavior needed by the macOS MVP:

- realtime partial text for the floating panel
- final text after user stop
- local-only execution
- reusable long-running model process
- no change to hotkeys, focus detection, clipboard, paste, or floating panel safety

## Evidence Used

Local result directories:

- `eval/asr_streaming/results/qwen3-asr-0.6b-full-20260622-100827`
- `eval/asr_streaming/results/qwen3-asr-1.7b-full-20260622-102709`
- `eval/asr_streaming/results/mimo-v25-asr-mlx-full-20260622-114759`

Local docs and code inspected:

- `.external/models/Qwen3-ASR-0.6B/README.md`
- `.external/models/Qwen3-ASR-1.7B/README.md`
- `.venv/lib/python3.11/site-packages/qwen_asr/inference/qwen3_asr.py`
- `.venv/lib/python3.11/site-packages/qwen_asr/cli/demo_streaming.py`
- `.external/repos/mlx-audio/mlx_audio/stt/models/qwen3_asr/README.md`
- `.external/repos/mlx-audio/mlx_audio/stt/models/qwen3_asr/qwen3_asr.py`
- `.external/repos/mlx-audio/mlx_audio/stt/models/mimo_v2_asr/README.md`
- `.external/repos/mlx-audio/mlx_audio/stt/models/mimo_v2_asr/asr.py`
- `.external/repos/mlx-audio-main-src/mlx-audio-main/mlx_audio/stt/models/nemotron_asr/nemotron_asr.py`
- `.external/repos/MiMo-V2.5-ASR-MLX/run_mimo_asr_mlx.py`
- `eval/asr_streaming/model_registry.json`
- `specs/progress.md`

## File-Level Quality Snapshot

These numbers come from the same 10 local WAV cases. Lower CER, WER, RTF, and
final latency are better.

| Model | Supplier | Released | Params | Local model size | Mean CER | Mean WER | Mean RTF | Mean final latency |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR 0.6B | Alibaba / Qwen | 2026-01-29 | 0.6B | 1.8G | 0.0470 | 0.1918 | 0.1264 | 3291 ms |
| Qwen3-ASR 1.7B | Alibaba / Qwen | 2026-01-29 | 1.7B | 4.4G | 0.0431 | 0.1760 | 0.1849 | 5065 ms |
| MiMo-V2.5-ASR MLX | Xiaomi MiMo | 2026-06-02 | 8B | 4.2G + 2.4G tokenizer | 0.0311 | 0.1613 | 0.1214 | 3217 ms |

Interpretation:

- MiMo-V2.5-ASR MLX is the best file-level candidate on this local set.
- Qwen3-ASR 1.7B is slightly more accurate than Qwen3-ASR 0.6B, but slower in the current CPU file-level path.
- Qwen3-ASR 0.6B remains attractive because its quality is close to 1.7B with lower model size and lower file-level latency.
- All three still need hotword/context correction for product and model names such as `Qwen3-ASR`, `MiMo-V2.5-ASR`, `LocalVoiceInput`, and module names.

## Runtime Capability Findings

### Qwen3-ASR official `qwen-asr` path

Current local evaluation used the `qwen-asr` transformers backend in file-level
mode. This path is validated for local offline final transcription, but not for
floating-panel realtime partials.

Runtime facts:

- The package exposes `init_streaming_state`, `streaming_transcribe`, and `finish_streaming_transcribe`.
- Local source requires `backend == "vllm"` for all three streaming methods.
- Current `.venv` does not have the `vllm` package installed.
- The bundled streaming demo posts float32 PCM chunks to `/api/chunk` and calls `asr.streaming_transcribe(...)`, which is the right shape for our future local service.
- The official README says streaming is only available with the vLLM backend. Its vLLM installation example targets CUDA nightly wheels (`cu129`), so MacBook Pro M4 feasibility is not proven.
- The official streaming implementation re-feeds all audio accumulated so far on each chunk; it is incremental at the service API level, but not a fully cached acoustic stream.

Risk:

- Do not integrate this into the macOS app until a local vLLM or alternative Apple Silicon streaming runtime is proven.

### Qwen3-ASR MLX path in `mlx-audio`

`mlx-audio` includes Qwen3-ASR MLX implementations and documents:

- `mlx-community/Qwen3-ASR-0.6B-8bit`
- `mlx-community/Qwen3-ASR-1.7B-8bit`
- CLI `--stream`
- Python `model.stream_transcribe("audio.wav", ...)`

Runtime facts:

- The MLX class exposes `generate(..., stream=True)`, `stream_transcribe(...)`, and `stream_generate(...)`.
- `stream_transcribe(...)` yields token-level `StreamingResult` values.
- The current API accepts a complete audio file/array, splits it into chunks internally, and streams tokens during generation.
- Runtime probe on the locally loaded 0.6B and 1.7B MLX snapshots confirms `generate`, `stream_transcribe`, and `stream_generate` are present, but `create_streaming_session` is not present.
- It is not a stateful microphone session API that accepts PCM chunks as the user is speaking.
- Prefix-audio diagnostics on `zh_short_001` can emit tokens quickly from the first 2 seconds of an already materialized buffer, but that is not equivalent to a realtime gate pass.
- Cumulative recompute probe on `qwen3-asr-0.6b-mlx-8bit` is promising as a future wrapper experiment but still not native realtime streaming:
  - Smoke `zh_short_001`: first meaningful simulated partial from the 2s prefix, visible at about `2086ms`; serial recompute RTF `0.1065`; final CER/WER `0.1053`; final text confused `语音` as `云`.
  - Long `long_120_001`: first meaningful simulated partial from the 1s prefix, visible at about `1106ms`; tested prefixes through 8s; serial recompute RTF `0.1214`; final CER/WER `0.0082`; final text confused `本机` as `手机`.
  - Result directories: `eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-smoke-20260622` and `eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-long120-20260622`.
- In-process cumulative service prototype validates the wrapper session contract but remains outside the Swift app:
  - Self-test covers old session event rejection, late partial rejection after final, and cancel producing no final.
  - Smoke `zh_short_001`: `service_gate_passed=true`; 6 partials before stop; 1 final after stop; first usable partial about `2078ms`; final latency about `137ms`; final CER/WER `0.1053`.
  - Long `long_120_001`: `service_gate_passed=true`; 8 partials before stop; 1 final after stop; first usable partial about `1092ms`; final latency about `603ms`; final CER/WER `0.0082`.
  - Result directories: `eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-smoke-20260622` and `eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-long120-20260622`.

Risk:

- This remains useful for file-level quality and possible custom service experiments, but it should not be integrated as the MVP realtime backend unless a session-style wrapper is built and passes the realtime gate.
- A cumulative wrapper would need scheduling, cancellation, stale-result isolation, and an equivalent timed-PCM gate before any Swift app integration.
- The current service prototype is in-process. Swift integration still needs a real local service boundary and separate macOS runtime validation.

### MiMo-V2.5-ASR MLX path

MiMo is validated locally through the `mimo-asr-mlx-local` file-level adapter and
the official helper script.

Runtime facts:

- The MiMo MLX class exposes `generate(audio, ...)`.
- It does not expose `stream_transcribe`, `stream_generate`, or `generate_streaming`.
- Its `generate(...)` implementation loads the full audio, encodes full audio codes, builds one prompt, calls the model once, and returns one final `STTOutput`.
- Extra kwargs are ignored (`del kwargs`), so passing a `stream=True` style flag would not enable streaming.
- Observed MiMo helper cold command: about 60.5s wall time and about 9.17GB peak memory footprint for one short WAV.
- Observed full 10-case MiMo harness command: about 28.1GB peak memory footprint. Treat this as command-level evidence, not yet steady long-running service RSS.

Risk:

- MiMo should not be selected as the default realtime App backend yet, despite its strong file-level quality, because it does not currently provide realtime partials for the floating panel.

### Nemotron 3.5 ASR Streaming 0.6B MLX path

Nemotron is labeled as a streaming FastConformer-RNNT model, and its local
MLX implementation provides cache-aware `stream_generate(audio)` over a provided
audio buffer.

Runtime facts:

- The local main-source implementation exposes `generate(...)` and `stream_generate(...)`.
- It does not expose `stream_transcribe`, `generate_streaming`, or `create_streaming_session`.
- The generic STT loader in the local main-source checkout has the implementation directory but lacks a `nemotron_asr` remapping entry; the evaluation probe uses a narrow in-process remapping shim rather than editing vendored source.
- Surface probe output directory: `eval/asr_streaming/results/nemotron-mlx-realtime-surface-probe-20260622`.
- File-level quality is weak on the current 10 local WAV cases: mean CER `0.3090`, mean WER `0.2993`, mean RTF `0.0177`.

Risk:

- Do not treat the word `streaming` in the model name as proof of LocalVoiceInput realtime eligibility. With the current local MLX runtime, Nemotron is cache-aware file streaming, not a microphone PCM session backend.
- Because local Chinese and technical-term quality is already weak, Nemotron should be lower priority than Qwen3 MLX wrapper work unless a true session runtime appears.

## Recommendation

Do not integrate a new backend into the macOS app yet.

Ranked next steps:

1. Validate Qwen3-ASR 0.6B MLX 8-bit as the next runtime spike.
   - Download `mlx-community/Qwen3-ASR-0.6B-8bit`.
   - Run the same 10-case file-level harness through MLX if practical.
   - Build a tiny local service simulation that feeds a WAV as timed PCM chunks and records partial cadence, final quality, model load time, and steady RSS.
   - This is the best current path because it is Apple Silicon native and has explicit token streaming APIs.

2. Keep MiMo-V2.5-ASR MLX as the current quality benchmark and potential final-only backend.
   - It is the best file-level model so far.
   - It can be useful as an offline final correction/benchmark candidate only if latency and memory are acceptable.
   - It should not drive the floating panel partial path without a proven chunked or streaming design.

3. Keep official Qwen3-ASR 0.6B / 1.7B as validated file-level baselines.
   - The official streaming shape is good for our eventual service contract.
   - The vLLM dependency is the blocker on MacBook Pro M4.
   - If MLX Qwen quality is weak, revisit official vLLM feasibility or a remote-but-LAN-local test machine only as a separate decision.

4. Do not prioritize Qwen3-ASR 1.7B for the first runtime spike.
   - It is slightly more accurate than 0.6B in file-level CPU mode.
   - It is slower and larger.
   - Use it after the 0.6B service shape is proven.

5. Do not prioritize Nemotron 3.5 ASR Streaming 0.6B MLX for the first app backend.
   - It is fast and has cache-aware `stream_generate(audio)`, but no local session API was found.
   - Its local Chinese/technical-term quality is much weaker than Qwen3 and MiMo on the current cases.

## Backend Service Shape To Prove Next

The next spike should stay independent from the Swift app and expose a local
service contract equivalent to:

- `start(session_id, options)`
- `push_pcm(session_id, pcm16k_mono_float32_or_int16)`
- `partial(session_id, text, revision, is_final=false)`
- `finish(session_id)`
- `final(session_id, text, is_final=true)`
- `cancel(session_id)`

Required checks:

- old session events are ignored
- late partial cannot overwrite final
- user stop, not backend offline segment, controls finalization
- RTF remains below 1 on 200-400 word dictation
- first usable partial appears quickly enough for the floating panel
- service keeps one model loaded across sessions
- memory footprint is acceptable on MacBook Pro M4 / 48GB

## Current Decision

For the next implementation step, do not wire Qwen3-ASR MLX directly into the
macOS App. The in-process cumulative service prototype has passed smoke and
`long_120_001`; next, create a real local process boundary for the same service
contract, then test it before Swift integration. MiMo remains the strongest
file-level model, but not a realtime partial backend yet.
