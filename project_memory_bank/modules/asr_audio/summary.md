# ASR And Audio Module

The ASR/audio path is local-first and supports mock validation, real FunASR WebSocket 2-pass transcription, and an optional localhost HTTP ASR client for the Qwen3-ASR MLX cumulative service.

Stable responsibilities:

- `AudioCapture` records microphone input with `AVAudioEngine`, converts to 16 kHz mono int16 PCM, batches chunks, and flushes pending PCM before ASR finish.
- `FunASRClient` connects to a local WebSocket endpoint, sends a 2-pass start message, streams PCM data, and sends `is_speaking=false` after audio flush.
- `LocalHTTPASRClient` connects to an explicitly selected loopback HTTP service, posts `/start`, `/chunk`, `/finish`, and `/cancel`, transfers PCM as base64 JSON, and filters backend events by session token before emitting `ASREvent` values.
- `MockASRClient` provides deterministic partial and final events for interaction testing without a server.
- `ASRClientProtocol` keeps the app controller independent of the concrete ASR source.
- The local FunASR websocket runtime can run against cached smoke-test model directories under `.external/models/` for offline ASR, online ASR, and VAD.
- `eval/asr_streaming/` is the independent backend evaluation harness for replaying 16 kHz mono int16 WAV files before changing the macOS app runtime.
- `eval/asr_streaming/realtime_gate.py` is the stricter realtime backend gate: it sends timed PCM chunks, requires partials before simulated user stop, requires final/offline output after stop, and rejects late partials after final.
- `scripts/record_asr_cases.sh` starts the guided local recording flow for ASR eval cases and saves case-aligned WAV files under `eval/asr_streaming/audio/`.
- `eval/asr_streaming/run_eval.py` also supports a local Fun-ASR-Nano file-level adapter for model comparison on the same WAV cases without touching macOS hotkey, focus, paste, or floating-panel code.
- `eval/asr_streaming/qwen3_mlx_realtime_probe.py` checks whether Qwen3-ASR MLX exposes true session streaming or only file/token streaming.
- Qwen3-ASR MLX 0.6B and 1.7B expose `generate`, `stream_transcribe`, and `stream_generate`, but not `create_streaming_session`; they are not realtime-gate eligible without a custom session wrapper.
- `eval/asr_streaming/qwen3_mlx_cumulative_probe.py` measures whether Qwen3-ASR MLX can be periodically rerun on accumulated audio prefixes as a future local wrapper strategy; it does not mark the model as native realtime-gate eligible.
- Qwen3-ASR MLX 0.6B cumulative recompute is promising on current local smoke and `long_120_001` probes, and the optional Swift HTTP client now validates client-side token filtering and cancel suppression; any default app path still requires process supervision, real app smoke, and resource limits.
- `eval/asr_streaming/qwen3_mlx_cumulative_service.py` validates an in-process wrapper service contract around Qwen3-ASR MLX cumulative recompute, including session token ownership, timed `push_pcm`, partial/final events, cancel behavior, and stale-result rejection.
- `eval/asr_streaming/qwen3_mlx_http_service.py` exposes that cumulative wrapper behind local HTTP JSON endpoints compatible with `incremental_ux_gate.py --adapter http-json`.
- `eval/asr_streaming/monitor_pid_resources.py` and `scripts/run_qwen3_mlx_http_extended_gate.sh` provide repeatable RSS/CPU sampling while the Qwen3 HTTP gate runs.
- `eval/asr_streaming/segment_cache_eval.py` prepares bounded segment WAVs and analyzes segment-final results as source-case plus strategy reports. Its first validated runs support using hybrid segmented caching for long dictation instead of whole-session cumulative final recompute.
- Qwen3-ASR MLX 0.6B passes the current local HTTP process-boundary gate on smoke, `long_120_001`, and the extended long-case subset (`long_200_001`, `long_400_001`, `long_code_switch_001`); the Swift app now has a validated optional HTTP client path, but this is still not a direct replacement of the existing FunASR app backend.
- The Qwen3 MLX HTTP service currently uses single-threaded `HTTPServer` because MLX inference failed when model load and request handling ran on different Python threads.
- The first extended Qwen3 HTTP resource run observed about 1.4 GB peak RSS and low mean CPU with bursty peaks; these are initial sizing signals, not final acceptance thresholds.
- Nemotron 3.5 ASR Streaming 0.6B MLX exposes cache-aware `stream_generate(audio)` in the local MLX implementation, but the local runtime surface does not expose a session-style incremental PCM API; current local Chinese/technical-term quality is weak.
- MiMo-V2.5-ASR MLX remains the offline-quality reference unless a chunked or streaming API is proven.
- The local ASR model cache is intentionally lean after cleanup: keep Qwen3-ASR MLX 0.6B/1.7B for the current wrapper path, MiMo-V2.5-ASR MLX plus tokenizer for offline reference, and FunASR Paraformer/VAD for baseline/runtime fallback. Detailed cache paths and removed historical models live in `eval/asr_streaming/model_inventory.md`.
- AMD model acquisition can be used as a cache/transfer path for large Hugging Face snapshots, but Mac-local inference remains the authoritative product evidence.
- `scripts/download_fun_asr_nano.sh` and `scripts/run_fun_asr_nano_smoke.sh` provide the repeatable acquisition and smoke path for Fun-ASR-Nano-2512.

Important constraints:

- FunASR offline segment results can update transcript state while recording but must not finalize the whole user session until user stop.
- The websocket server must flush remaining PCM to offline ASR when `is_speaking=false` arrives, because the macOS app sends that control message after all PCM has been flushed.
- Old ASR sessions must not affect the active session.
- Real ASR setup should remain local; no audio or text is uploaded by default.
- Public ASR benchmark results are shortlist evidence only; final backend selection must be validated with local harness runs and project/user-specific recordings.
- Fun-ASR-Nano local file-level results are backend-selection evidence only. They do not validate realtime partial display, WebSocket session behavior, or macOS app insertion behavior.
- Qwen3-ASR MLX file/token streaming probes are backend-selection evidence only; current loaded MLX snapshots do not provide a native session API for timed microphone PCM chunks, partial stability, cancellation, and repeated-session model reuse.
- Qwen3-ASR MLX cumulative recompute probes and HTTP service gates are wrapper-feasibility evidence only. They are not native realtime streaming; the optional Swift client must still pass real app smoke before becoming a user-facing default.
- The validated Qwen3 cumulative service boundary and Swift HTTP client prove local process-boundary and client protocol feasibility, but this path is not yet the default app backend because it lacks process supervision, memory/CPU ceilings, and manual app-smoke validation.
- Cumulative-wrapper timing must be session-relative. A new recording session must not inherit previous-session worker delay.
- Long-dictation finalization should be bounded by segment budgets rather than a single whole-session final recompute. The exact product thresholds remain open, but the stable direction is a hybrid policy: hard audio-duration cap, soft recognized-text budget, silence/punctuation boundary preference, and backlog pressure controls.
- Long code-switch technical terms remain a quality risk even when the incremental UX gate passes; model prompting, hotword correction, final correction, or a larger final model may still be needed.
- Model names or cards that say `streaming` are not enough. The local runtime must expose or be wrapped into a tested `start/push_pcm/partial/finish/final/cancel` contract before app integration.
- Complete-audio `generate(...)` output, even when token-streamed after loading the whole file, is not enough to qualify a backend for the realtime floating-panel MVP.
- On FunASR 1.3.1, Fun-ASR-Nano should run without VAD by default until the Nano plus VAD merge failure is resolved.

Go Deeper:

- See `../../core/system_overview.md` for end-to-end flow.
- See `../../core/current_focus.md` for current real-ASR setup status.
- See `../../insights/funasr_local_runtime.md` for local FunASR and Fun-ASR-Nano operating notes.
