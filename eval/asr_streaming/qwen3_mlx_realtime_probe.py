#!/usr/bin/env python3
"""Probe Qwen3-ASR MLX for true realtime session eligibility.

This script separates three concepts:

1. true session streaming: feed PCM chunks, step decoder, close session
2. file/token streaming: stream tokens after complete audio is already available
3. prefix diagnostics: run the model on the first N seconds of a WAV

Only (1) is eligible for LocalVoiceInput's realtime gate.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_eval import (  # noqa: E402
    METRIC_EXPLANATIONS_ZH,
    cer,
    load_cases,
    load_model_metadata,
    now_ms,
    read_wav_16k_mono_int16,
    wer,
    write_json,
)


PROBE_SCHEMA_VERSION = "1.0"

PROBE_EXPLANATIONS_ZH = {
    **METRIC_EXPLANATIONS_ZH,
    "true_session_streaming": "真正的实时会话流式能力。模型或服务必须能接收连续 PCM chunk，并在 close 前通过 step/drain 产出 partial。",
    "file_token_streaming": "完整音频已可用后，模型在生成文本 token 时逐个返回。这不等同于麦克风实时输入。",
    "prefix_audio_probe": "只取 WAV 前 N 秒运行一次转写，用于估计早期音频能否产生可用文本；它不是 realtime gate 通过证据。",
    "realtime_gate_eligible": "是否有资格进入 realtime gate。当前规则要求存在 session-style API 或等价本地服务合同。",
}


REQUIRED_SESSION_METHODS = ["create_streaming_session"]
TOKEN_STREAM_METHODS = ["stream_transcribe", "stream_generate"]


def signature_for(obj: Any, name: str) -> str | None:
    if not hasattr(obj, name):
        return None
    try:
        return str(inspect.signature(getattr(obj, name)))
    except Exception as exc:
        return f"<signature unavailable: {exc}>"


def classify_model_surface(model: Any) -> dict[str, Any]:
    methods = {
        name: {
            "present": hasattr(model, name),
            "signature": signature_for(model, name),
        }
        for name in [
            "generate",
            "stream_transcribe",
            "stream_generate",
            "generate_streaming",
            "create_streaming_session",
        ]
    }
    generate_signature = methods["generate"]["signature"] or ""
    generate_has_stream_arg = "stream" in generate_signature
    missing_session = [name for name in REQUIRED_SESSION_METHODS if not methods[name]["present"]]
    token_streaming = any(methods[name]["present"] for name in TOKEN_STREAM_METHODS) or generate_has_stream_arg
    true_session = not missing_session
    return {
        "methods": methods,
        "true_session_streaming": {
            "supported": true_session,
            "required_methods": REQUIRED_SESSION_METHODS,
            "missing_methods": missing_session,
        },
        "file_token_streaming": {
            "supported": token_streaming,
            "evidence": {
                "stream_transcribe": methods["stream_transcribe"]["present"],
                "stream_generate": methods["stream_generate"]["present"],
                "generate_stream_arg": generate_has_stream_arg,
            },
        },
        "realtime_gate_eligible": true_session,
        "realtime_gate_eligibility_reason": (
            "session_api_present"
            if true_session
            else "missing_session_api_for_incremental_pcm_feed_step_close"
        ),
    }


def wav_to_float32(audio_path: Path, prefix_seconds: float | None = None) -> tuple[np.ndarray, float]:
    wav = read_wav_16k_mono_int16(audio_path)
    pcm = np.frombuffer(wav.pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if prefix_seconds is not None:
        sample_count = max(1, min(len(pcm), int(wav.sample_rate * prefix_seconds)))
        pcm = pcm[:sample_count]
    return pcm, len(pcm) / float(wav.sample_rate)


def extract_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(result, dict) and isinstance(result.get("text"), str):
        return str(result["text"])
    return str(result)


def run_prefix_smoke(
    *,
    model: Any,
    case_path: Path,
    expected_text: str,
    language: str | None,
    prefix_seconds: float,
    max_tokens: int,
) -> dict[str, Any]:
    prefix_audio, prefix_duration = wav_to_float32(case_path, prefix_seconds=prefix_seconds)
    full_audio, full_duration = wav_to_float32(case_path, prefix_seconds=None)

    prefix_events: list[dict[str, Any]] = []
    prefix_started = time.perf_counter()
    prefix_text_parts: list[str] = []
    first_prefix_token_ms: float | None = None

    if hasattr(model, "stream_transcribe"):
        for item in model.stream_transcribe(prefix_audio, language=language, max_tokens=max_tokens):
            text = extract_text(item)
            if not text:
                continue
            offset_ms = (time.perf_counter() - prefix_started) * 1000.0
            if first_prefix_token_ms is None:
                first_prefix_token_ms = offset_ms
            prefix_text_parts.append(text)
            prefix_events.append(
                {
                    "kind": "prefix_token",
                    "recv_offset_ms": offset_ms,
                    "text": text,
                    "is_final": bool(getattr(item, "is_final", False)),
                }
            )
    prefix_finished = time.perf_counter()
    prefix_text = "".join(prefix_text_parts).strip()

    final_started = time.perf_counter()
    final_result = model.generate(full_audio, language=language, max_tokens=max_tokens)
    final_finished = time.perf_counter()
    final_text = extract_text(final_result).strip()

    return {
        "kind": "prefix_audio_probe",
        "not_equivalent_to_realtime_gate": True,
        "reason_not_realtime_gate": "model is called on a materialized prefix buffer; no persistent feed/step/close session is used",
        "case_audio": str(case_path),
        "prefix_seconds": prefix_seconds,
        "prefix_audio_duration_seconds": prefix_duration,
        "full_audio_duration_seconds": full_duration,
        "prefix_text": prefix_text,
        "prefix_events": prefix_events,
        "prefix_event_count": len(prefix_events),
        "first_prefix_token_ms": first_prefix_token_ms,
        "prefix_wall_ms": (prefix_finished - prefix_started) * 1000.0,
        "final_text": final_text,
        "final_wall_ms": (final_finished - final_started) * 1000.0,
        "cer": cer(expected_text, final_text),
        "wer": wer(expected_text, final_text),
    }


def load_mlx_model(model_path: str, mlx_audio_source: str):
    source = Path(mlx_audio_source)
    if source.exists():
        sys.path.insert(0, str(source.resolve()))
    from mlx_audio.stt import load, utils as stt_utils

    config_path = Path(model_path) / "config.json"
    if config_path.exists():
        try:
            model_type = json.loads(config_path.read_text(encoding="utf-8")).get("model_type")
        except Exception:
            model_type = None
        # Some local mlx-audio snapshots contain the implementation directory but
        # miss the generic STT loader remapping. Patch only known local ASR model
        # types so runtime probes remain reproducible without editing vendored code.
        if model_type in {"nemotron_asr"} and hasattr(stt_utils, "MODEL_REMAPPING"):
            stt_utils.MODEL_REMAPPING.setdefault(model_type, model_type)

    return load(model_path)


def command_probe(args: argparse.Namespace) -> int:
    cases = load_cases(Path(args.cases), allow_missing_audio=False)
    case = cases[0]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)

    started = time.perf_counter()
    model = load_mlx_model(args.model, args.mlx_audio_source)
    load_wall_ms = (time.perf_counter() - started) * 1000.0
    surface = classify_model_surface(model)

    prefix_smoke = None
    if args.run_prefix_smoke:
        prefix_smoke = run_prefix_smoke(
            model=model,
            case_path=case.audio_path,
            expected_text=case.expected_text,
            language=args.language.strip() or None,
            prefix_seconds=args.prefix_seconds,
            max_tokens=args.max_tokens,
        )

    summary = {
        "probe_schema_version": PROBE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "model": args.model,
        "model_id": args.model_id,
        "model_info": model_info,
        "metric_explanations_zh": PROBE_EXPLANATIONS_ZH,
        "model_load_wall_ms": load_wall_ms,
        "case_id": case.case_id,
        "expected_text": case.expected_text,
        "api_surface": surface,
        "prefix_audio_probe": prefix_smoke,
        "final_recommendation": {
            "realtime_gate_eligible": bool(surface["realtime_gate_eligible"]),
            "use_as_app_realtime_backend_now": False,
            "reason": (
                "The loaded MLX STT model exposes file/token streaming over provided audio buffers, "
                "but it does not expose create_streaming_session/feed/step/close."
            ),
        },
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def command_self_test(args: argparse.Namespace) -> int:
    class TokenOnly:
        def generate(self, audio, *, stream=False):
            return None

        def stream_transcribe(self, audio):
            yield "x"

    class SessionCapable:
        def generate(self, audio):
            return None

        def create_streaming_session(self):
            return None

    token_surface = classify_model_surface(TokenOnly())
    if token_surface["realtime_gate_eligible"]:
        raise AssertionError(f"token-only model must not be gate eligible: {token_surface}")
    if not token_surface["file_token_streaming"]["supported"]:
        raise AssertionError(f"token-only model should report file token streaming: {token_surface}")

    session_surface = classify_model_surface(SessionCapable())
    if not session_surface["realtime_gate_eligible"]:
        raise AssertionError(f"session-capable model should be gate eligible: {session_surface}")

    print("Qwen3 MLX realtime probe self-test passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    self_test = sub.add_parser("self-test", help="Run surface-classification self-tests.")
    self_test.set_defaults(func=command_self_test)

    probe = sub.add_parser("probe", help="Probe a local Qwen3-ASR MLX model.")
    probe.add_argument("--model", default=".external/models/mlx-community__Qwen3-ASR-0.6B-8bit")
    probe.add_argument("--model-id", default="qwen3-asr-0.6b-mlx-8bit")
    probe.add_argument("--mlx-audio-source", default=".external/repos/mlx-audio")
    probe.add_argument("--cases", default="eval/asr_streaming/cases.smoke.local.jsonl")
    probe.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    probe.add_argument("--language", default="Chinese")
    probe.add_argument("--prefix-seconds", type=float, default=2.0)
    probe.add_argument("--max-tokens", type=int, default=256)
    probe.add_argument("--run-prefix-smoke", action="store_true")
    probe.add_argument("--out-dir", default="eval/asr_streaming/results/qwen3-mlx-realtime-probe")
    probe.set_defaults(func=command_probe)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
