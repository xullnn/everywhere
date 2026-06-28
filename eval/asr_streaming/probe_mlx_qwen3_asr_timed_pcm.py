#!/usr/bin/env python3
"""Timed PCM smoke probe for the community mlx-qwen3-asr streaming API.

This script is intentionally independent from the macOS app. It answers one
question: can the local mlx-qwen3-asr package accept microphone-like PCM chunks
through init_streaming/feed_audio/finish_streaming and produce usable pre-stop
partial plus post-stop final output?
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_eval import (  # noqa: E402
    DEFAULT_MIN_COMPLETE_TEXT_RATIO,
    EvalCase,
    append_jsonl,
    cer,
    char_length_ratio,
    json_safe,
    load_cases,
    monotonic_ms,
    now_ms,
    partial_rewrite_rate,
    read_wav_16k_mono_int16,
    wer,
    write_json,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "1.0"
DEFAULT_MODEL = ".external/models/mlx-community__Qwen3-ASR-0.6B-8bit"
DEFAULT_CASES = "eval/asr_streaming/cases.long_prepared.local.jsonl"

TIMED_PCM_METRIC_EXPLANATIONS_ZH: dict[str, str] = {
    "CER": "字符错误率，Character Error Rate，越低越好。按标准答案字符级编辑距离除以标准答案字符数计算。",
    "WER": "词或 token 错误率，Word Error Rate，越低越好。中文近似按单字 token，英文/数字按连续 token。",
    "RTF": "实时因子，Real Time Factor，等于总处理耗时除以音频时长。小于 1 表示快于音频实时长度，大于 1 表示慢于实时。",
    "TTFP": "首个 partial 延迟，Time To First Partial，从开始喂音频到第一次出现实时文字的时间。",
    "partial_cadence_ms": "partial 平均更新间隔，单位毫秒，越低表示浮窗更新越频繁。",
    "final_latency_ms": "停止输入后到 final 完成的延迟，单位毫秒，越低表示松开快捷键后等待越短。",
    "partial_stability": "partial 稳定度，来自 mlx-qwen3-asr 的 stable_text/text 比例，越高表示已稳定文本占比越高。",
    "rewrite_rate": "mlx-qwen3-asr 内部统计的改写率，越高表示实时文本越容易被后续片段改写。",
    "partial_rewrite_rate": "相邻 partial 文本的外部粗略变化率，越高表示浮窗文字越不稳定。",
    "finalization_delta_chars": "finish 阶段新增字符数，越大说明松开后还有较多尾部内容才被补上。",
    "partial_before_stop_count": "模拟用户停止前已经出现的 partial 数量，大于 0 才符合实时浮窗体验。",
    "final_after_stop_count": "模拟用户停止后出现的 final 数量，大于 0 才符合最终输出流程。",
    "selection_gate_passed": "候选可接入门槛。除 partial/final 时序外，还要求 CER/WER 不超过配置阈值。",
}


@dataclass
class ImportedStreamingAPI:
    package: Any
    session_class: Any
    streaming_metrics: Any
    mlx_core: Any


def timestamp_slug() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def source_commit(source_dir: Path | None) -> str | None:
    if source_dir is None or not (source_dir / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def source_metadata(source_dir: Path | None) -> dict[str, Any]:
    return {
        "source_dir": str(source_dir) if source_dir else None,
        "source_dir_exists": bool(source_dir and source_dir.exists()),
        "git_commit": source_commit(source_dir),
    }


def dtype_from_name(mx: Any, name: str) -> Any:
    normalized = name.strip().lower()
    if normalized == "float32":
        return mx.float32
    if normalized == "bfloat16":
        return mx.bfloat16
    return mx.float16


def import_streaming_api(source_dir: Path | None) -> ImportedStreamingAPI:
    if source_dir:
        if not source_dir.exists():
            raise FileNotFoundError(f"source dir not found: {source_dir}")
        sys.path.insert(0, str(source_dir.resolve()))

    package = importlib.import_module("mlx_qwen3_asr")
    session_module = importlib.import_module("mlx_qwen3_asr.session")
    streaming_module = importlib.import_module("mlx_qwen3_asr.streaming")
    mx = importlib.import_module("mlx.core")
    return ImportedStreamingAPI(
        package=package,
        session_class=getattr(session_module, "Session"),
        streaming_metrics=getattr(streaming_module, "streaming_metrics"),
        mlx_core=mx,
    )


def summarize_traceback(exc: BaseException) -> dict[str, Any]:
    return {
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(limit=8),
    }


def selected_cases(args: argparse.Namespace) -> list[EvalCase]:
    cases_path = resolve_path(args.cases)
    if cases_path is None:
        raise ValueError("--cases is required")
    cases = load_cases(cases_path)
    if args.only_id:
        wanted = set(args.only_id)
        cases = [case for case in cases if case.case_id in wanted]
    if args.case_limit is not None:
        cases = cases[: max(0, int(args.case_limit))]
    if not cases:
        raise ValueError("no cases selected")
    return cases


def average_gap_ms(events: list[dict[str, Any]]) -> float | None:
    offsets = [float(e["recv_offset_ms"]) for e in events if e.get("recv_offset_ms") is not None]
    if len(offsets) < 2:
        return None
    gaps = [b - a for a, b in zip(offsets, offsets[1:])]
    return sum(gaps) / len(gaps)


def make_failure_summary(
    *,
    out_dir: Path,
    args: argparse.Namespace,
    stage: str,
    exc: BaseException,
    source_dir: Path | None,
    model_path: Path | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "probe": "mlx-qwen3-asr-timed-pcm-smoke",
        "created_epoch_ms": now_ms(),
        "status": stage,
        "dry_run": bool(args.dry_run),
        "source": source_metadata(source_dir),
        "model": str(model_path) if model_path else args.model,
        "metric_explanations_zh": TIMED_PCM_METRIC_EXPLANATIONS_ZH,
        "local_voice_input_realtime_eligible_now": False,
        "eligibility_reason": stage,
        "error": summarize_traceback(exc),
        "args": vars(args),
    }
    write_json(out_dir / "summary.json", payload)
    return payload


def feed_case(
    *,
    case: EvalCase,
    out_dir: Path,
    session: Any,
    api: ImportedStreamingAPI,
    args: argparse.Namespace,
) -> dict[str, Any]:
    import numpy as np

    audio = read_wav_16k_mono_int16(case.audio_path)
    samples = np.frombuffer(audio.pcm, dtype="<i2")
    feed_samples = max(1, int(audio.sample_rate * (args.feed_chunk_ms / 1000.0)))
    case_out = out_dir / case.case_id
    case_out.mkdir(parents=True, exist_ok=True)
    events_path = case_out / "events.jsonl"
    if events_path.exists():
        events_path.unlink()

    state = session.init_streaming(
        context=args.context or "",
        language=args.language,
        unfixed_chunk_num=args.unfixed_chunk_num,
        unfixed_token_num=args.unfixed_token_num,
        chunk_size_sec=args.stream_chunk_sec,
        max_context_sec=args.max_context_sec,
        sample_rate=audio.sample_rate,
        max_new_tokens=args.max_new_tokens,
        finalization_mode=args.finalization_mode,
        endpointing_mode=args.endpointing_mode,
    )

    run_started = time.perf_counter()
    last_partial_text = ""
    last_stable_text = ""
    partial_events: list[dict[str, Any]] = []
    chunk_events: list[dict[str, Any]] = []

    for chunk_index, start_sample in enumerate(range(0, len(samples), feed_samples), start=1):
        end_sample = min(len(samples), start_sample + feed_samples)
        pcm_chunk = samples[start_sample:end_sample].copy()
        audio_start_ms = (start_sample / audio.sample_rate) * 1000.0
        audio_end_ms = (end_sample / audio.sample_rate) * 1000.0
        feed_started = time.perf_counter()
        session.feed_audio(pcm_chunk, state)
        feed_ms = (time.perf_counter() - feed_started) * 1000.0
        recv_offset_ms = monotonic_ms(run_started)

        chunk_event = {
            "kind": "chunk_fed",
            "case_id": case.case_id,
            "chunk_index": chunk_index,
            "audio_start_ms": audio_start_ms,
            "audio_end_ms": audio_end_ms,
            "recv_offset_ms": recv_offset_ms,
            "feed_call_latency_ms": feed_ms,
            "sample_count": int(len(pcm_chunk)),
            "decoded_chunk_id": int(getattr(state, "chunk_id", 0)),
            "accepted": False,
            "is_final": False,
        }
        chunk_events.append(chunk_event)
        append_jsonl(events_path, chunk_event)

        current_text = str(getattr(state, "text", "") or "")
        current_stable = str(getattr(state, "stable_text", "") or "")
        if current_text and (current_text != last_partial_text or current_stable != last_stable_text):
            partial_event = {
                "kind": "partial",
                "case_id": case.case_id,
                "chunk_index": chunk_index,
                "audio_end_ms": audio_end_ms,
                "recv_offset_ms": recv_offset_ms,
                "text": current_text,
                "stable_text": current_stable,
                "accepted": True,
                "is_final": False,
            }
            partial_events.append(partial_event)
            append_jsonl(events_path, partial_event)
            last_partial_text = current_text
            last_stable_text = current_stable

        if args.realtime_sleep:
            target_elapsed = end_sample / float(audio.sample_rate)
            actual_elapsed = time.perf_counter() - run_started
            if actual_elapsed < target_elapsed:
                time.sleep(target_elapsed - actual_elapsed)

    input_finished_offset_ms = monotonic_ms(run_started)
    finish_started = time.perf_counter()
    session.finish_streaming(state)
    finish_call_latency_ms = (time.perf_counter() - finish_started) * 1000.0
    run_finished_offset_ms = monotonic_ms(run_started)
    run_finished = time.perf_counter()

    final_text = str(getattr(state, "text", "") or "")
    final_event = {
        "kind": "final",
        "case_id": case.case_id,
        "recv_offset_ms": run_finished_offset_ms,
        "input_finished_offset_ms": input_finished_offset_ms,
        "finish_call_latency_ms": finish_call_latency_ms,
        "text": final_text,
        "stable_text": str(getattr(state, "stable_text", "") or ""),
        "accepted": bool(final_text),
        "is_final": True,
    }
    append_jsonl(events_path, final_event)

    metrics = dict(api.streaming_metrics(state))
    partial_texts = [str(e.get("text", "")) for e in partial_events]
    final_after_stop_count = 1 if final_event["accepted"] and run_finished_offset_ms >= input_finished_offset_ms else 0
    coverage = char_length_ratio(final_text, case.expected_text)
    cer_value = cer(case.expected_text, final_text)
    wer_value = wer(case.expected_text, final_text)
    gate_fail_reasons: list[str] = []
    if not partial_events:
        gate_fail_reasons.append("no_partial_before_stop")
    if final_after_stop_count == 0:
        gate_fail_reasons.append("no_final_after_stop")
    if not final_text:
        gate_fail_reasons.append("empty_final_text")
    if coverage is not None and coverage < args.min_final_coverage:
        gate_fail_reasons.append("low_final_coverage")
    selection_fail_reasons = list(gate_fail_reasons)
    if cer_value is not None and cer_value > args.max_cer_for_eligibility:
        selection_fail_reasons.append("high_cer")
    if wer_value is not None and wer_value > args.max_wer_for_eligibility:
        selection_fail_reasons.append("high_wer")

    summary = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case.case_id,
        "status": "ok" if not gate_fail_reasons else "gate_failed",
        "gate_fail_reasons": gate_fail_reasons,
        "selection_gate_fail_reasons": selection_fail_reasons,
        "timed_pcm_gate_passed": not gate_fail_reasons,
        "selection_gate_passed": not selection_fail_reasons,
        "input_realtime_pacing": bool(args.realtime_sleep),
        "audio": str(case.audio_path),
        "duration_seconds": audio.duration_seconds,
        "lang": case.lang,
        "scenario": case.scenario,
        "expected_text": case.expected_text,
        "final_text": final_text,
        "metric_explanations_zh": TIMED_PCM_METRIC_EXPLANATIONS_ZH,
        "CER": cer_value,
        "WER": wer_value,
        "RTF": (run_finished - run_started) / max(0.001, audio.duration_seconds),
        "TTFP_ms": partial_events[0]["recv_offset_ms"] if partial_events else None,
        "partial_cadence_ms": average_gap_ms(partial_events),
        "final_latency_ms": run_finished_offset_ms - input_finished_offset_ms,
        "partial_before_stop_count": len(partial_events),
        "final_after_stop_count": final_after_stop_count,
        "partial_event_count": len(partial_events),
        "chunk_event_count": len(chunk_events),
        "partial_rewrite_rate": partial_rewrite_rate(partial_texts),
        "final_to_expected_char_ratio": coverage,
        "streaming_metrics": json_safe(metrics),
        "partial_stability": metrics.get("partial_stability"),
        "rewrite_rate": metrics.get("rewrite_rate"),
        "finalization_delta_chars": metrics.get("finalization_delta_chars"),
        "input_finished_offset_ms": input_finished_offset_ms,
        "finish_call_latency_ms": finish_call_latency_ms,
        "events_path": str(events_path),
    }
    write_json(case_out / "summary.json", summary)
    return summary


def build_aggregate(
    *,
    out_dir: Path,
    args: argparse.Namespace,
    source_dir: Path | None,
    model_path: Path | None,
    model_info: dict[str, Any] | None,
    cases: list[dict[str, Any]],
    status: str,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    passed_cases = [
        case
        for case in cases
        if case.get("selection_gate_passed", case.get("timed_pcm_gate_passed"))
    ]
    failed_cases = [
        case
        for case in cases
        if not case.get("selection_gate_passed", case.get("timed_pcm_gate_passed"))
    ]
    all_cases_passed = bool(cases) and len(passed_cases) == len(cases)
    if not cases:
        eligibility_reason = status
    elif not args.realtime_sleep:
        eligibility_reason = "non_realtime_compatibility_mode"
    elif not all_cases_passed:
        eligibility_reason = "one_or_more_cases_failed_selection_gate"
    else:
        eligibility_reason = "all_cases_passed_realtime_paced_timed_pcm_gate"

    local_voice_input_eligible = bool(args.realtime_sleep and all_cases_passed and status == "ok")
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "probe": "mlx-qwen3-asr-timed-pcm-smoke",
        "created_epoch_ms": now_ms(),
        "status": status,
        "dry_run": bool(args.dry_run),
        "source": source_metadata(source_dir),
        "model": str(model_path) if model_path else args.model,
        "model_info": json_safe(model_info or {}),
        "metric_explanations_zh": TIMED_PCM_METRIC_EXPLANATIONS_ZH,
        "input_realtime_pacing": bool(args.realtime_sleep),
        "local_voice_input_realtime_eligible_now": local_voice_input_eligible,
        "eligibility_reason": eligibility_reason,
        "case_count": len(cases),
        "passed_case_count": len(passed_cases),
        "failed_case_count": len(failed_cases),
        "case_summaries": cases,
        "error": error,
        "args": vars(args),
        "result_dir": str(out_dir),
    }
    write_json(out_dir / "summary.json", aggregate)
    return aggregate


def command_run(args: argparse.Namespace) -> int:
    out_dir = resolve_path(args.out_dir)
    if out_dir is None:
        out_dir = ROOT / "eval" / "asr_streaming" / "results" / f"mlx-qwen3-asr-timed-pcm-{timestamp_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = resolve_path(args.source_dir)
    model_path = resolve_path(args.model)
    if model_path is not None and not model_path.exists():
        model_arg = args.model
    else:
        model_arg = str(model_path) if model_path is not None else args.model

    if args.dry_run:
        cases_preview: list[dict[str, Any]] = []
        try:
            cases_preview = [
                {
                    "case_id": case.case_id,
                    "audio": str(case.audio_path),
                    "scenario": case.scenario,
                    "lang": case.lang,
                }
                for case in selected_cases(args)
            ]
        except Exception as exc:  # noqa: BLE001
            cases_preview = [{"selection_error": str(exc)}]
        build_aggregate(
            out_dir=out_dir,
            args=args,
            source_dir=source_dir,
            model_path=model_path,
            model_info={"dry_run": True, "would_load_model": model_arg},
            cases=[],
            status="dry_run",
            error={"cases_preview": cases_preview},
        )
        print(json.dumps({"status": "dry_run", "result_dir": str(out_dir)}, ensure_ascii=False))
        return 0

    try:
        api = import_streaming_api(source_dir)
    except Exception as exc:  # noqa: BLE001
        make_failure_summary(
            out_dir=out_dir,
            args=args,
            stage="import_failed",
            exc=exc,
            source_dir=source_dir,
            model_path=model_path,
        )
        print(json.dumps({"status": "import_failed", "result_dir": str(out_dir), "error": str(exc)}, ensure_ascii=False))
        return 1 if args.strict else 0

    try:
        dtype = dtype_from_name(api.mlx_core, args.dtype)
        session = api.session_class(model=model_arg, dtype=dtype)
        model_info = dict(getattr(session, "model_info", {}) or {})
    except Exception as exc:  # noqa: BLE001
        make_failure_summary(
            out_dir=out_dir,
            args=args,
            stage="model_load_failed",
            exc=exc,
            source_dir=source_dir,
            model_path=model_path,
        )
        print(json.dumps({"status": "model_load_failed", "result_dir": str(out_dir), "error": str(exc)}, ensure_ascii=False))
        return 1 if args.strict else 0

    try:
        cases = selected_cases(args)
    except Exception as exc:  # noqa: BLE001
        make_failure_summary(
            out_dir=out_dir,
            args=args,
            stage="case_selection_failed",
            exc=exc,
            source_dir=source_dir,
            model_path=model_path,
        )
        print(json.dumps({"status": "case_selection_failed", "result_dir": str(out_dir), "error": str(exc)}, ensure_ascii=False))
        return 1 if args.strict else 0

    case_summaries: list[dict[str, Any]] = []
    api_errors: list[dict[str, Any]] = []
    for case in cases:
        try:
            case_summaries.append(
                feed_case(
                    case=case,
                    out_dir=out_dir,
                    session=session,
                    api=api,
                    args=args,
                )
            )
        except Exception as exc:  # noqa: BLE001
            error = summarize_traceback(exc)
            api_errors.append({"case_id": case.case_id, **error})
            case_summaries.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "case_id": case.case_id,
                    "status": "api_failed",
                    "timed_pcm_gate_passed": False,
                    "gate_fail_reasons": ["api_failed"],
                    "error": error,
                }
            )

    status = "ok" if not api_errors else "api_failed"
    aggregate = build_aggregate(
        out_dir=out_dir,
        args=args,
        source_dir=source_dir,
        model_path=model_path,
        model_info=model_info,
        cases=case_summaries,
        status=status,
        error={"api_errors": api_errors} if api_errors else None,
    )
    print(
        json.dumps(
            {
                "status": aggregate["status"],
                "result_dir": str(out_dir),
                "eligible": aggregate["local_voice_input_realtime_eligible_now"],
                "eligibility_reason": aggregate["eligibility_reason"],
                "passed_case_count": aggregate["passed_case_count"],
                "case_count": aggregate["case_count"],
            },
            ensure_ascii=False,
        )
    )
    if args.strict and not aggregate["local_voice_input_realtime_eligible_now"]:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=".external/repos/mlx-qwen3-asr")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cases", default=DEFAULT_CASES)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-id", action="append", default=[])
    parser.add_argument("--case-limit", type=int, default=None)
    parser.add_argument("--feed-chunk-ms", type=float, default=48.0)
    parser.add_argument("--stream-chunk-sec", type=float, default=2.0)
    parser.add_argument("--max-context-sec", type=float, default=30.0)
    parser.add_argument("--unfixed-chunk-num", type=int, default=2)
    parser.add_argument("--unfixed-token-num", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--finalization-mode", choices=["accuracy", "latency"], default="accuracy")
    parser.add_argument("--endpointing-mode", choices=["fixed", "energy"], default="fixed")
    parser.add_argument("--language", default=None)
    parser.add_argument("--context", default="")
    parser.add_argument("--dtype", choices=["float16", "float32", "bfloat16"], default="float16")
    parser.add_argument("--min-final-coverage", type=float, default=DEFAULT_MIN_COMPLETE_TEXT_RATIO)
    parser.add_argument("--max-cer-for-eligibility", type=float, default=0.10)
    parser.add_argument("--max-wer-for-eligibility", type=float, default=0.25)
    parser.add_argument("--strict", action="store_true", help="Return non-zero when the candidate is not eligible.")
    sleep_group = parser.add_mutually_exclusive_group()
    sleep_group.add_argument("--realtime-sleep", dest="realtime_sleep", action="store_true", default=False)
    sleep_group.add_argument("--no-realtime-sleep", dest="realtime_sleep", action="store_false")
    return parser


def main() -> int:
    return command_run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
