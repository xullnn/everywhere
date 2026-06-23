#!/usr/bin/env python3
"""Probe Qwen3-ASR MLX cumulative recompute as a realtime-wrapper candidate.

This script tests a specific fallback architecture:

1. keep receiving microphone PCM chunks in an app/service wrapper
2. periodically run Qwen3-ASR MLX on the accumulated prefix audio
3. treat each prefix result as a simulated partial
4. run the full audio once after user stop for the final result

This is not native session streaming. It does not prove realtime-gate
eligibility, because each prefix is reprocessed from the beginning and no
persistent feed/step/close decoder state is used.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwen3_mlx_realtime_probe import (  # noqa: E402
    classify_model_surface,
    extract_text,
    load_mlx_model,
)
from run_eval import (  # noqa: E402
    METRIC_EXPLANATIONS_ZH,
    append_jsonl,
    cer,
    char_length_ratio,
    load_cases,
    load_model_metadata,
    merge_partial_texts,
    normalize_for_cer,
    now_ms,
    partial_rewrite_rate,
    read_wav_16k_mono_int16,
    wer,
    write_json,
)


CUMULATIVE_SCHEMA_VERSION = "1.0"

CUMULATIVE_EXPLANATIONS_ZH = {
    **METRIC_EXPLANATIONS_ZH,
    "cumulative_recompute_probe": "累计重算探针。把同一段音频按 1s/2s/3s 等前缀反复送入模型，观察是否可作为自建实时 wrapper 的 partial 来源。",
    "native_realtime_gate_eligible": "是否满足原生实时 gate 资格。累计重算不会打开 feed/step/close 会话，因此这里固定为 false。",
    "prefix_wall_ms": "单次前缀推理墙钟耗时，单位毫秒。越低越可能支撑实时 partial。",
    "prefix_compute_rtf": "单次前缀推理 RTF，等于该前缀推理耗时除以前缀音频时长。小于 1 表示这一次前缀推理快于对应音频时长。",
    "first_usable_partial_user_visible_ms": "从用户开始说话到第一个非空模拟 partial 可见的估算时间，约等于前缀音频时长加该前缀推理耗时。",
    "queued_partial_latency_ms": "假设单 worker 串行处理所有前缀时，某个前缀准备好以后还要等多久才能拿到结果。",
    "serial_recompute_rtf": "累计重算总耗时除以最后一个被测试前缀的音频时长。大于 1 表示按当前频率串行重算会追不上输入。",
    "prefix_rewrite_rate": "相邻模拟 partial 文本的平均变化率。越高表示浮窗文本越不稳定。",
    "custom_wrapper_viability": "累计重算 wrapper 是否值得继续工程化。它不是 realtime gate 通过结论。",
}


def has_meaningful_text(text: str) -> bool:
    return bool(normalize_for_cer(text))


def prefix_has_meaningful_text(prefix: dict[str, Any]) -> bool:
    if "meaningful_text" in prefix:
        return bool(prefix["meaningful_text"])
    return has_meaningful_text(str(prefix.get("text", "")))


def wav_to_float32(audio_path: Path) -> tuple[np.ndarray, float]:
    wav = read_wav_16k_mono_int16(audio_path)
    pcm = np.frombuffer(wav.pcm, dtype="<i2").astype(np.float32) / 32768.0
    return pcm, wav.duration_seconds


def prefix_seconds_for_duration(
    *,
    duration_seconds: float,
    min_prefix_sec: float,
    prefix_step_sec: float,
    max_prefixes: int,
) -> list[float]:
    if duration_seconds <= 0:
        return []
    min_prefix_sec = max(0.1, min_prefix_sec)
    prefix_step_sec = max(0.1, prefix_step_sec)
    max_prefixes = max(1, max_prefixes)

    values: list[float] = []
    current = min(min_prefix_sec, duration_seconds)
    while len(values) < max_prefixes and current < duration_seconds:
        rounded = round(current, 3)
        if not values or rounded > values[-1]:
            values.append(rounded)
        current += prefix_step_sec

    if not values:
        values.append(round(duration_seconds, 3))
    return values


def call_stream_or_generate(
    *,
    model: Any,
    audio: np.ndarray,
    language: str | None,
    max_tokens: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    first_token_ms: float | None = None
    events: list[dict[str, Any]] = []
    text_parts: list[str] = []
    mode = "stream_transcribe" if hasattr(model, "stream_transcribe") else "generate"

    if mode == "stream_transcribe":
        for item in model.stream_transcribe(audio, language=language, max_tokens=max_tokens):
            text = extract_text(item)
            if not text:
                continue
            offset_ms = (time.perf_counter() - started) * 1000.0
            if first_token_ms is None:
                first_token_ms = offset_ms
            text_parts.append(text)
            events.append(
                {
                    "kind": "prefix_token",
                    "recv_offset_ms": offset_ms,
                    "text": text,
                    "is_final": bool(getattr(item, "is_final", False)),
                }
            )
        text = merge_partial_texts(text_parts)
    else:
        result = model.generate(audio, language=language, max_tokens=max_tokens)
        text = extract_text(result).strip()
        if text:
            first_token_ms = (time.perf_counter() - started) * 1000.0
            events.append(
                {
                    "kind": "prefix_generate_result",
                    "recv_offset_ms": first_token_ms,
                    "text": text,
                    "is_final": True,
                }
            )

    finished = time.perf_counter()
    return {
        "mode": mode,
        "text": text.strip(),
        "first_token_ms": first_token_ms,
        "wall_ms": (finished - started) * 1000.0,
        "events": events,
    }


def call_final_generate(
    *,
    model: Any,
    audio: np.ndarray,
    language: str | None,
    max_tokens: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    result = model.generate(audio, language=language, max_tokens=max_tokens)
    finished = time.perf_counter()
    return {
        "text": extract_text(result).strip(),
        "wall_ms": (finished - started) * 1000.0,
        "mode": "generate",
    }


def add_serial_queue_metrics(prefixes: list[dict[str, Any]]) -> None:
    worker_available_ms = 0.0
    for prefix in prefixes:
        scheduled_ms = float(prefix["prefix_seconds"]) * 1000.0
        wall_ms = float(prefix["prefix_wall_ms"])
        worker_start_ms = max(scheduled_ms, worker_available_ms)
        worker_finish_ms = worker_start_ms + wall_ms
        prefix["serial_worker_start_delay_ms"] = worker_start_ms - scheduled_ms
        prefix["queued_partial_latency_ms"] = worker_finish_ms - scheduled_ms
        worker_available_ms = worker_finish_ms


def classify_custom_wrapper(
    *,
    case_summary: dict[str, Any],
    max_prefix_wall_ms: float,
    max_queued_partial_latency_ms: float,
    max_first_usable_partial_user_visible_ms: float,
    max_final_wall_ms: float,
    max_final_cer: float,
    max_serial_recompute_rtf: float,
) -> dict[str, Any]:
    prefixes = list(case_summary["prefixes"])
    nonempty = [p for p in prefixes if prefix_has_meaningful_text(p)]
    fail_reasons: list[str] = []
    warnings: list[str] = []

    if not nonempty:
        fail_reasons.append("no_nonempty_prefix_text")
    else:
        first = nonempty[0]
        if float(first["first_usable_partial_user_visible_ms"]) > max_first_usable_partial_user_visible_ms:
            fail_reasons.append("first_usable_partial_too_slow")
        max_observed_wall = max(float(p["prefix_wall_ms"]) for p in nonempty)
        if max_observed_wall > max_prefix_wall_ms:
            fail_reasons.append("prefix_compute_too_slow")
        max_observed_queue = max(float(p["queued_partial_latency_ms"]) for p in nonempty)
        if max_observed_queue > max_queued_partial_latency_ms:
            fail_reasons.append("serial_queue_latency_too_slow")

    serial_rtf = case_summary.get("serial_recompute_rtf")
    if isinstance(serial_rtf, (int, float)) and float(serial_rtf) > max_serial_recompute_rtf:
        fail_reasons.append("serial_recompute_rtf_too_high")

    final_cer = case_summary.get("cer")
    if not isinstance(final_cer, (int, float)):
        fail_reasons.append("missing_final_cer")
    elif float(final_cer) > max_final_cer:
        fail_reasons.append("final_cer_too_high")

    if float(case_summary["final_wall_ms"]) > max_final_wall_ms:
        warnings.append("final_generate_slow_for_stop_latency")

    rewrite_rate = case_summary.get("prefix_rewrite_rate")
    if isinstance(rewrite_rate, (int, float)) and rewrite_rate > 0.75:
        warnings.append("prefix_text_unstable")

    scenario = str(case_summary.get("scenario", ""))
    duration_seconds = float(case_summary.get("duration_seconds", 0.0))
    if fail_reasons:
        viability = "not_viable_for_cumulative_recompute"
    elif scenario.startswith("long") or duration_seconds >= 30.0:
        viability = "promising_for_tested_long_case_not_native_realtime"
    else:
        viability = "promising_smoke_only_requires_long_form_validation"

    return {
        "native_realtime_gate_eligible": False,
        "not_equivalent_to_realtime_gate": True,
        "custom_wrapper_viability": viability,
        "custom_wrapper_fail_reasons": fail_reasons,
        "custom_wrapper_warnings": warnings,
        "thresholds": {
            "max_prefix_wall_ms": max_prefix_wall_ms,
            "max_queued_partial_latency_ms": max_queued_partial_latency_ms,
            "max_first_usable_partial_user_visible_ms": max_first_usable_partial_user_visible_ms,
            "max_final_wall_ms": max_final_wall_ms,
            "max_final_cer": max_final_cer,
            "max_serial_recompute_rtf": max_serial_recompute_rtf,
        },
        "reason_not_native_realtime": (
            "Each simulated partial is produced by rerunning the model on a materialized prefix. "
            "No persistent incremental PCM session or decoder cache is used."
        ),
        "use_as_app_realtime_backend_now": False,
    }


def run_case(
    *,
    model: Any,
    case: Any,
    model_info: dict[str, Any],
    out_dir: Path,
    language: str | None,
    min_prefix_sec: float,
    prefix_step_sec: float,
    max_prefixes: int,
    max_tokens: int,
    max_prefix_wall_ms: float,
    max_queued_partial_latency_ms: float,
    max_first_usable_partial_user_visible_ms: float,
    max_final_wall_ms: float,
    max_final_cer: float,
    max_serial_recompute_rtf: float,
) -> dict[str, Any]:
    case_out = out_dir / case.case_id
    events_path = case_out / "prefix_events.jsonl"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    full_audio, duration_seconds = wav_to_float32(case.audio_path)
    sample_rate = 16000
    prefixes: list[dict[str, Any]] = []
    for prefix_sec in prefix_seconds_for_duration(
        duration_seconds=duration_seconds,
        min_prefix_sec=min_prefix_sec,
        prefix_step_sec=prefix_step_sec,
        max_prefixes=max_prefixes,
    ):
        sample_count = max(1, min(len(full_audio), int(prefix_sec * sample_rate)))
        actual_prefix_sec = sample_count / float(sample_rate)
        prefix_audio = full_audio[:sample_count]
        result = call_stream_or_generate(
            model=model,
            audio=prefix_audio,
            language=language,
            max_tokens=max_tokens,
        )
        prefix_wall_ms = float(result["wall_ms"])
        prefix_summary = {
            "prefix_seconds": actual_prefix_sec,
            "prefix_wall_ms": prefix_wall_ms,
            "prefix_compute_rtf": prefix_wall_ms / max(1.0, actual_prefix_sec * 1000.0),
            "first_token_ms": result["first_token_ms"],
            "text": result["text"],
            "meaningful_text": has_meaningful_text(str(result["text"])),
            "text_to_expected_char_ratio": char_length_ratio(str(result["text"]), case.expected_text),
            "mode": result["mode"],
            "event_count": len(result["events"]),
        }
        prefix_summary["first_usable_partial_user_visible_ms"] = (
            actual_prefix_sec * 1000.0 + prefix_wall_ms
            if prefix_summary["meaningful_text"]
            else None
        )
        prefixes.append(prefix_summary)
        for event in result["events"]:
            event_record = {
                **event,
                "case_id": case.case_id,
                "prefix_seconds": actual_prefix_sec,
                "recv_epoch_ms": now_ms(),
            }
            append_jsonl(events_path, event_record)

    add_serial_queue_metrics(prefixes)

    final = call_final_generate(
        model=model,
        audio=full_audio,
        language=language,
        max_tokens=max_tokens,
    )
    prefix_texts = [str(p.get("text", "")) for p in prefixes if bool(p.get("meaningful_text"))]
    last_prefix_sec = float(prefixes[-1]["prefix_seconds"]) if prefixes else 0.0
    serial_total_wall_ms = sum(float(p["prefix_wall_ms"]) for p in prefixes)
    case_summary = {
        "schema_version": CUMULATIVE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "case_id": case.case_id,
        "model_info": model_info,
        "metric_explanations_zh": CUMULATIVE_EXPLANATIONS_ZH,
        "audio": str(case.audio_path),
        "duration_seconds": duration_seconds,
        "lang": case.lang,
        "scenario": case.scenario,
        "expected_text": case.expected_text,
        "prefix_probe_config": {
            "min_prefix_sec": min_prefix_sec,
            "prefix_step_sec": prefix_step_sec,
            "max_prefixes": max_prefixes,
            "max_tokens": max_tokens,
        },
        "prefixes": prefixes,
        "prefix_rewrite_rate": partial_rewrite_rate(prefix_texts),
        "serial_recompute_total_wall_ms": serial_total_wall_ms,
        "serial_recompute_rtf": (
            serial_total_wall_ms / max(1.0, last_prefix_sec * 1000.0)
            if last_prefix_sec > 0
            else None
        ),
        "final_text": final["text"],
        "final_wall_ms": final["wall_ms"],
        "final_mode": final["mode"],
        "cer": cer(case.expected_text, str(final["text"])),
        "wer": wer(case.expected_text, str(final["text"])),
    }
    case_summary["custom_wrapper_assessment"] = classify_custom_wrapper(
        case_summary=case_summary,
        max_prefix_wall_ms=max_prefix_wall_ms,
        max_queued_partial_latency_ms=max_queued_partial_latency_ms,
        max_first_usable_partial_user_visible_ms=max_first_usable_partial_user_visible_ms,
        max_final_wall_ms=max_final_wall_ms,
        max_final_cer=max_final_cer,
        max_serial_recompute_rtf=max_serial_recompute_rtf,
    )
    write_json(case_out / "summary.json", case_summary)
    return case_summary


def filter_cases(cases: list[Any], selected_ids: list[str]) -> list[Any]:
    if not selected_ids:
        return cases
    wanted: set[str] = set()
    for raw in selected_ids:
        wanted.update(part.strip() for part in raw.split(",") if part.strip())
    filtered = [case for case in cases if case.case_id in wanted]
    missing = sorted(wanted - {case.case_id for case in filtered})
    if missing:
        raise ValueError(f"case ids not found: {', '.join(missing)}")
    return filtered


def aggregate_status(case_summaries: list[dict[str, Any]]) -> str:
    if not case_summaries:
        return "no_cases"
    if all(not s["custom_wrapper_assessment"]["custom_wrapper_fail_reasons"] for s in case_summaries):
        return "all_tested_cases_promising_not_native_realtime"
    if any(not s["custom_wrapper_assessment"]["custom_wrapper_fail_reasons"] for s in case_summaries):
        return "mixed"
    return "not_viable_for_tested_cases"


def command_run(args: argparse.Namespace) -> int:
    cases = filter_cases(load_cases(Path(args.cases), allow_missing_audio=False), args.case_id)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)

    started = time.perf_counter()
    model = load_mlx_model(args.model, args.mlx_audio_source)
    load_wall_ms = (time.perf_counter() - started) * 1000.0
    surface = classify_model_surface(model)

    case_summaries = [
        run_case(
            model=model,
            case=case,
            model_info=model_info,
            out_dir=out_dir,
            language=args.language.strip() or None,
            min_prefix_sec=args.min_prefix_sec,
            prefix_step_sec=args.prefix_step_sec,
            max_prefixes=args.max_prefixes,
            max_tokens=args.max_tokens,
            max_prefix_wall_ms=args.max_prefix_wall_ms,
            max_queued_partial_latency_ms=args.max_queued_partial_latency_ms,
            max_first_usable_partial_user_visible_ms=args.max_first_usable_partial_user_visible_ms,
            max_final_wall_ms=args.max_final_wall_ms,
            max_final_cer=args.max_final_cer,
            max_serial_recompute_rtf=args.max_serial_recompute_rtf,
        )
        for case in cases
    ]
    summary = {
        "schema_version": CUMULATIVE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "model": args.model,
        "model_id": args.model_id,
        "model_info": model_info,
        "metric_explanations_zh": CUMULATIVE_EXPLANATIONS_ZH,
        "model_load_wall_ms": load_wall_ms,
        "api_surface": surface,
        "case_count": len(case_summaries),
        "case_ids": [case["case_id"] for case in case_summaries],
        "aggregate_status": aggregate_status(case_summaries),
        "native_realtime_gate_eligible": False,
        "not_equivalent_to_realtime_gate": True,
        "case_summaries": case_summaries,
        "final_recommendation": {
            "use_as_app_realtime_backend_now": False,
            "reason": (
                "Cumulative recompute can only become an app backend after a separate local service "
                "implements scheduling, cancellation, and stale-result isolation, then passes an equivalent realtime gate."
            ),
        },
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def command_self_test(args: argparse.Namespace) -> int:
    fast_case = {
        "case_id": "fake_short",
        "scenario": "short_dictation",
        "duration_seconds": 4.0,
        "prefixes": [
            {
                "prefix_seconds": 1.0,
                "prefix_wall_ms": 120.0,
                "queued_partial_latency_ms": 120.0,
                "first_usable_partial_user_visible_ms": None,
                "text": "",
            },
            {
                "prefix_seconds": 2.0,
                "prefix_wall_ms": 180.0,
                "queued_partial_latency_ms": 180.0,
                "first_usable_partial_user_visible_ms": 2180.0,
                "text": "你好",
            },
        ],
        "serial_recompute_rtf": 0.15,
        "final_wall_ms": 500.0,
        "cer": 0.0,
        "prefix_rewrite_rate": 0.1,
    }
    fast = classify_custom_wrapper(
        case_summary=fast_case,
        max_prefix_wall_ms=1200,
        max_queued_partial_latency_ms=1500,
        max_first_usable_partial_user_visible_ms=2500,
        max_final_wall_ms=2500,
        max_final_cer=0.15,
        max_serial_recompute_rtf=1.0,
    )
    if fast["native_realtime_gate_eligible"]:
        raise AssertionError("cumulative recompute must never be marked native realtime")
    if fast["custom_wrapper_fail_reasons"]:
        raise AssertionError(f"fast fake case should be promising: {fast}")

    slow_case = {
        **fast_case,
        "prefixes": [
            {
                "prefix_seconds": 2.0,
                "prefix_wall_ms": 1800.0,
                "queued_partial_latency_ms": 1800.0,
                "first_usable_partial_user_visible_ms": 3800.0,
                "text": "你好",
            }
        ],
        "serial_recompute_rtf": 0.9,
    }
    slow = classify_custom_wrapper(
        case_summary=slow_case,
        max_prefix_wall_ms=1200,
        max_queued_partial_latency_ms=1500,
        max_first_usable_partial_user_visible_ms=2500,
        max_final_wall_ms=2500,
        max_final_cer=0.15,
        max_serial_recompute_rtf=1.0,
    )
    if "prefix_compute_too_slow" not in slow["custom_wrapper_fail_reasons"]:
        raise AssertionError(f"slow fake case should fail prefix latency: {slow}")

    no_text_case = {**fast_case, "prefixes": [{**fast_case["prefixes"][0]}]}
    no_text = classify_custom_wrapper(
        case_summary=no_text_case,
        max_prefix_wall_ms=1200,
        max_queued_partial_latency_ms=1500,
        max_first_usable_partial_user_visible_ms=2500,
        max_final_wall_ms=2500,
        max_final_cer=0.15,
        max_serial_recompute_rtf=1.0,
    )
    if "no_nonempty_prefix_text" not in no_text["custom_wrapper_fail_reasons"]:
        raise AssertionError(f"empty prefix text should fail: {no_text}")

    print("Qwen3 MLX cumulative recompute probe self-test passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    self_test = sub.add_parser("self-test", help="Run cumulative wrapper classification self-tests.")
    self_test.set_defaults(func=command_self_test)

    run = sub.add_parser("run", help="Run cumulative recompute probe against a local Qwen3-ASR MLX model.")
    run.add_argument("--model", default=".external/models/mlx-community__Qwen3-ASR-0.6B-8bit")
    run.add_argument("--model-id", default="qwen3-asr-0.6b-mlx-8bit")
    run.add_argument("--mlx-audio-source", default=".external/repos/mlx-audio")
    run.add_argument("--cases", default="eval/asr_streaming/cases.smoke.local.jsonl")
    run.add_argument("--case-id", action="append", default=[], help="Case id to run; can be repeated or comma-separated.")
    run.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    run.add_argument("--language", default="Chinese")
    run.add_argument("--min-prefix-sec", type=float, default=1.0)
    run.add_argument("--prefix-step-sec", type=float, default=1.0)
    run.add_argument("--max-prefixes", type=int, default=6)
    run.add_argument("--max-tokens", type=int, default=256)
    run.add_argument("--max-prefix-wall-ms", type=float, default=1200.0)
    run.add_argument("--max-queued-partial-latency-ms", type=float, default=1500.0)
    run.add_argument("--max-first-usable-partial-user-visible-ms", type=float, default=2500.0)
    run.add_argument("--max-final-wall-ms", type=float, default=2500.0)
    run.add_argument("--max-final-cer", type=float, default=0.15)
    run.add_argument("--max-serial-recompute-rtf", type=float, default=1.0)
    run.add_argument("--out-dir", default="eval/asr_streaming/results/qwen3-mlx-cumulative-probe")
    run.set_defaults(func=command_run)

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
