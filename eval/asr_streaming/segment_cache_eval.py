#!/usr/bin/env python3
"""Prepare and analyze segmented-cache ASR evaluation runs.

This tool does not implement the production dictation runtime. It creates a
repeatable local harness for answering one narrower question: if long dictation
is finalized in bounded segments, which segment budgets look feasible for
Qwen3-ASR MLX style file-level final recognition?
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from run_eval import cer, load_cases, normalize_for_cer, read_wav_16k_mono_int16, wer, write_json


DEFAULT_SOURCE_CASES = Path("eval/asr_streaming/cases.long_prepared.local.jsonl")
DEFAULT_OUT_AUDIO_DIR = Path("eval/asr_streaming/audio/segment_cache")
DEFAULT_OUT_CASES = Path("eval/asr_streaming/cases.segment_cache.local.jsonl")
DEFAULT_OUT_MANIFEST = Path("eval/asr_streaming/results/segment-cache/manifest.json")
DEFAULT_STRATEGIES = [
    "s30_c150_o0:30:150:0",
    "s45_c250_o0:45:250:0",
    "s60_c250_o0:60:250:0",
    "s90_c400_o0:90:400:0",
]

METRIC_EXPLANATIONS_ZH: dict[str, str] = {
    "segment_count": "分段数量。数量越多，单段更短，但总调用次数更多。",
    "total_segment_audio_sec": "所有分段音频时长之和。启用重叠时会大于原始音频时长。",
    "total_model_wall_ms": "所有分段识别真实耗时相加，单位毫秒。它表示模型总工作量，不等于用户停止后的等待时间。",
    "max_segment_wall_ms": "最慢单个分段识别耗时，单位毫秒。它影响后台处理能否追上用户说话。",
    "serial_final_wait_ms": "假设只有一个后台模型 worker，用户说完后还需要等待多久才能拿到全部已提交分段的最终结果。",
    "serial_max_lag_ms": "假设一个后台模型 worker 时，分段处理完成时间落后于对应音频结束时间的最大值。越大表示后台越积压。",
    "cer": "字符错误率，越低越好。这里按拼接后的全部分段文本对比原始整段标准答案。",
    "wer": "词或 token 错误率，越低越好。中文近似按单字 token，英文/数字/符号按连续 token。",
    "coverage": "输出覆盖率，等于拼接输出归一化字符数除以标准答案归一化字符数。过低通常表示漏尾或漏段。",
    "strategy": "切段策略，格式包含硬性音频时长上限、软文字预算和重叠秒数。",
}


@dataclass(frozen=True)
class Strategy:
    strategy_id: str
    max_segment_sec: float
    soft_text_chars: int
    overlap_sec: float


@dataclass(frozen=True)
class SegmentPlan:
    source_case_id: str
    strategy: Strategy
    segment_index: int
    segment_count: int
    logical_start_sec: float
    logical_end_sec: float
    audio_start_sec: float
    audio_end_sec: float
    expected_text: str
    audio_path: Path

    @property
    def segment_id(self) -> str:
        return f"{self.source_case_id}__{self.strategy.strategy_id}__seg{self.segment_index:03d}"

    @property
    def logical_duration_sec(self) -> float:
        return self.logical_end_sec - self.logical_start_sec

    @property
    def audio_duration_sec(self) -> float:
        return self.audio_end_sec - self.audio_start_sec


def parse_strategy(value: str) -> Strategy:
    parts = value.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "strategy must use name:max_segment_sec:soft_text_chars:overlap_sec, "
            f"got {value!r}"
        )
    name = parts[0].strip()
    if not name:
        raise argparse.ArgumentTypeError("strategy name must not be empty")
    try:
        max_segment_sec = float(parts[1])
        soft_text_chars = int(parts[2])
        overlap_sec = float(parts[3])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid numeric strategy fields: {value!r}") from exc
    if max_segment_sec <= 0:
        raise argparse.ArgumentTypeError("max_segment_sec must be > 0")
    if soft_text_chars < 0:
        raise argparse.ArgumentTypeError("soft_text_chars must be >= 0")
    if overlap_sec < 0:
        raise argparse.ArgumentTypeError("overlap_sec must be >= 0")
    if overlap_sec >= max_segment_sec:
        raise argparse.ArgumentTypeError("overlap_sec must be smaller than max_segment_sec")
    return Strategy(
        strategy_id=name,
        max_segment_sec=max_segment_sec,
        soft_text_chars=soft_text_chars,
        overlap_sec=overlap_sec,
    )


def round3(value: float) -> float:
    return round(float(value), 3)


def relative_to(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return os.path.relpath(path, base)


def slice_text_by_time(text: str, start_sec: float, end_sec: float, duration_sec: float) -> str:
    if duration_sec <= 0 or not text:
        return ""
    start_index = int(round(len(text) * max(0.0, start_sec) / duration_sec))
    end_index = int(round(len(text) * min(duration_sec, end_sec) / duration_sec))
    if end_index <= start_index:
        end_index = min(len(text), start_index + 1)
    return text[start_index:end_index]


def target_segment_seconds(*, strategy: Strategy, source_text: str, source_duration_sec: float, min_segment_sec: float) -> float:
    target = strategy.max_segment_sec
    normalized_chars = len(normalize_for_cer(source_text))
    if strategy.soft_text_chars > 0 and normalized_chars > 0 and source_duration_sec > 0:
        chars_per_sec = normalized_chars / source_duration_sec
        if chars_per_sec > 0:
            text_budget_sec = strategy.soft_text_chars / chars_per_sec
            target = min(target, text_budget_sec)
    return max(min_segment_sec, min(strategy.max_segment_sec, target))


def plan_segments_for_case(
    *,
    case: Any,
    strategy: Strategy,
    out_audio_dir: Path,
    min_segment_sec: float,
) -> list[SegmentPlan]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    duration = audio.duration_seconds
    target_sec = target_segment_seconds(
        strategy=strategy,
        source_text=case.expected_text,
        source_duration_sec=duration,
        min_segment_sec=min_segment_sec,
    )
    plans: list[SegmentPlan] = []
    logical_start = 0.0
    while logical_start < duration - 0.001:
        logical_end = min(duration, logical_start + target_sec)
        audio_start = max(0.0, logical_start - strategy.overlap_sec if plans else logical_start)
        audio_end = logical_end
        expected = slice_text_by_time(case.expected_text, logical_start, logical_end, duration)
        placeholder = SegmentPlan(
            source_case_id=case.case_id,
            strategy=strategy,
            segment_index=len(plans) + 1,
            segment_count=0,
            logical_start_sec=logical_start,
            logical_end_sec=logical_end,
            audio_start_sec=audio_start,
            audio_end_sec=audio_end,
            expected_text=expected,
            audio_path=out_audio_dir / f"{case.case_id}__{strategy.strategy_id}__seg{len(plans) + 1:03d}.wav",
        )
        plans.append(placeholder)
        logical_start = logical_end
    segment_count = len(plans)
    return [
        SegmentPlan(
            source_case_id=item.source_case_id,
            strategy=item.strategy,
            segment_index=item.segment_index,
            segment_count=segment_count,
            logical_start_sec=item.logical_start_sec,
            logical_end_sec=item.logical_end_sec,
            audio_start_sec=item.audio_start_sec,
            audio_end_sec=item.audio_end_sec,
            expected_text=item.expected_text,
            audio_path=item.audio_path,
        )
        for item in plans
    ]


def write_segment_wav(source_audio_path: Path, segment: SegmentPlan) -> None:
    audio = read_wav_16k_mono_int16(source_audio_path)
    bytes_per_frame = audio.channels * audio.sample_width
    start_frame = int(round(segment.audio_start_sec * audio.sample_rate))
    end_frame = int(round(segment.audio_end_sec * audio.sample_rate))
    start_byte = max(0, start_frame * bytes_per_frame)
    end_byte = min(len(audio.pcm), end_frame * bytes_per_frame)
    segment.audio_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(segment.audio_path), "wb") as wav:
        wav.setnchannels(audio.channels)
        wav.setsampwidth(audio.sample_width)
        wav.setframerate(audio.sample_rate)
        wav.writeframes(audio.pcm[start_byte:end_byte])


def segment_record(*, segment: SegmentPlan, case: Any, out_cases: Path) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    estimated_chars_per_sec = len(normalize_for_cer(case.expected_text)) / max(0.001, audio.duration_seconds)
    return {
        "id": segment.segment_id,
        "audio": relative_to(segment.audio_path, out_cases.parent),
        "text": segment.expected_text,
        "lang": case.lang,
        "scenario": "segment_cache_eval",
        "metadata": {
            "purpose": "segmented_cache_eval",
            "metric_bearing": False,
            "source_case_id": case.case_id,
            "source_scenario": case.scenario,
            "source_audio": str(case.audio_path),
            "source_duration_seconds": round3(audio.duration_seconds),
            "source_expected_text": case.expected_text,
            "source_expected_chars": len(normalize_for_cer(case.expected_text)),
            "strategy_id": segment.strategy.strategy_id,
            "max_segment_seconds": segment.strategy.max_segment_sec,
            "soft_text_chars": segment.strategy.soft_text_chars,
            "overlap_seconds": segment.strategy.overlap_sec,
            "segment_index": segment.segment_index,
            "segment_count": segment.segment_count,
            "logical_start_seconds": round3(segment.logical_start_sec),
            "logical_end_seconds": round3(segment.logical_end_sec),
            "logical_duration_seconds": round3(segment.logical_duration_sec),
            "audio_start_seconds": round3(segment.audio_start_sec),
            "audio_end_seconds": round3(segment.audio_end_sec),
            "audio_duration_seconds": round3(segment.audio_duration_sec),
            "estimated_chars_per_second": round3(estimated_chars_per_sec),
            "text_alignment": "proportional_estimate_for_eval_only",
            "segment_metric_note_zh": (
                "本 segment 的标准文本按整段文本比例切分，只用于生成可复现 case；"
                "不要把单段 CER/WER 当作精确质量证据，应该看聚合后的整段指标。"
            ),
        },
    }


def command_prepare(args: argparse.Namespace) -> int:
    source_cases = load_cases(Path(args.source_cases))
    selected_ids = set(args.case_id or [])
    if selected_ids:
        source_cases = [case for case in source_cases if case.case_id in selected_ids]
        missing = selected_ids - {case.case_id for case in source_cases}
        if missing:
            raise ValueError(f"case id not found in {args.source_cases}: {', '.join(sorted(missing))}")
    strategies = [parse_strategy(item) for item in (args.strategy or DEFAULT_STRATEGIES)]
    out_audio_dir = Path(args.out_audio_dir)
    out_cases = Path(args.out_cases)
    out_manifest = Path(args.out_manifest)

    records: list[dict[str, Any]] = []
    manifest_cases: list[dict[str, Any]] = []
    for case in source_cases:
        audio = read_wav_16k_mono_int16(case.audio_path)
        case_entry: dict[str, Any] = {
            "source_case_id": case.case_id,
            "source_audio": str(case.audio_path),
            "source_duration_seconds": round3(audio.duration_seconds),
            "source_expected_text": case.expected_text,
            "source_expected_chars": len(normalize_for_cer(case.expected_text)),
            "lang": case.lang,
            "scenario": case.scenario,
            "strategies": [],
        }
        for strategy in strategies:
            segments = plan_segments_for_case(
                case=case,
                strategy=strategy,
                out_audio_dir=out_audio_dir,
                min_segment_sec=args.min_segment_sec,
            )
            strategy_entry = {
                "strategy_id": strategy.strategy_id,
                "max_segment_seconds": strategy.max_segment_sec,
                "soft_text_chars": strategy.soft_text_chars,
                "overlap_seconds": strategy.overlap_sec,
                "segment_count": len(segments),
                "segments": [],
                "evaluation_note_zh": (
                    "soft_text_chars 在这里通过标准答案长度估算切段点，只用于离线评测；"
                    "生产运行时不能依赖标准答案。"
                ),
            }
            for segment in segments:
                if not args.dry_run:
                    write_segment_wav(case.audio_path, segment)
                record = segment_record(segment=segment, case=case, out_cases=out_cases)
                records.append(record)
                strategy_entry["segments"].append(
                    {
                        "segment_id": segment.segment_id,
                        "segment_index": segment.segment_index,
                        "audio": record["audio"],
                        "logical_start_seconds": round3(segment.logical_start_sec),
                        "logical_end_seconds": round3(segment.logical_end_sec),
                        "audio_start_seconds": round3(segment.audio_start_sec),
                        "audio_end_seconds": round3(segment.audio_end_sec),
                        "audio_duration_seconds": round3(segment.audio_duration_sec),
                    }
                )
            case_entry["strategies"].append(strategy_entry)
        manifest_cases.append(case_entry)

    manifest = {
        "schema_version": "1.0",
        "created_epoch_ms": int(time.time() * 1000),
        "source_cases": str(args.source_cases),
        "out_cases": str(out_cases),
        "out_audio_dir": str(out_audio_dir),
        "dry_run": bool(args.dry_run),
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "cases": manifest_cases,
    }

    if not args.dry_run:
        out_cases.parent.mkdir(parents=True, exist_ok=True)
        with out_cases.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        write_json(out_manifest, manifest)

    print(
        json.dumps(
            {
                "dry_run": bool(args.dry_run),
                "source_case_count": len(source_cases),
                "strategy_count": len(strategies),
                "segment_case_count": len(records),
                "out_cases": str(out_cases),
                "out_manifest": str(out_manifest),
                "cases": [
                    {
                        "source_case_id": case["source_case_id"],
                        "source_duration_seconds": case["source_duration_seconds"],
                        "strategies": [
                            {
                                "strategy_id": item["strategy_id"],
                                "segment_count": item["segment_count"],
                                "max_segment_seconds": item["max_segment_seconds"],
                                "soft_text_chars": item["soft_text_chars"],
                                "overlap_seconds": item["overlap_seconds"],
                            }
                            for item in case["strategies"]
                        ],
                    }
                    for case in manifest_cases
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def load_segment_summaries(path: Path) -> dict[str, dict[str, Any]]:
    aggregate = json.loads(path.read_text(encoding="utf-8"))
    return {str(item.get("case_id")): item for item in aggregate.get("cases", [])}


def wall_ms_from_summary(summary: dict[str, Any] | None, fallback_duration_sec: float) -> float | None:
    if summary is None:
        return None
    rtf = summary.get("rtf")
    duration = summary.get("duration_seconds") or fallback_duration_sec
    if isinstance(rtf, (int, float)) and isinstance(duration, (int, float)):
        return float(rtf) * float(duration) * 1000.0
    return None


def coverage_ratio(expected_text: str, final_text: str) -> float | None:
    expected_len = len(normalize_for_cer(expected_text))
    if expected_len == 0:
        return 0.0 if normalize_for_cer(final_text) else None
    return len(normalize_for_cer(final_text)) / expected_len


def serial_worker_timing(rows: list[dict[str, Any]], source_duration_sec: float) -> dict[str, Any]:
    worker_free_sec = 0.0
    schedule: list[dict[str, Any]] = []
    for row in rows:
        submit_sec = float(row["logical_end_seconds"])
        wall_ms = row.get("wall_ms")
        process_sec = 0.0 if wall_ms is None else max(0.0, float(wall_ms) / 1000.0)
        start_sec = max(worker_free_sec, submit_sec)
        finish_sec = start_sec + process_sec
        worker_free_sec = finish_sec
        lag_ms = max(0.0, finish_sec - submit_sec) * 1000.0
        schedule.append(
            {
                "segment_id": row["segment_id"],
                "submit_sec": round3(submit_sec),
                "worker_start_sec": round3(start_sec),
                "worker_finish_sec": round3(finish_sec),
                "process_ms": None if wall_ms is None else round(float(wall_ms), 3),
                "lag_ms": round(lag_ms, 3),
            }
        )
    final_wait_ms = max(0.0, worker_free_sec - source_duration_sec) * 1000.0
    max_lag_ms = max((item["lag_ms"] for item in schedule), default=0.0)
    return {
        "serial_worker_schedule": schedule,
        "serial_final_wait_ms": round(final_wait_ms, 3),
        "serial_max_lag_ms": round(float(max_lag_ms), 3),
    }


def analyze_group(
    *,
    case_entry: dict[str, Any],
    strategy_entry: dict[str, Any],
    summaries: dict[str, dict[str, Any]],
    max_cer: float,
    min_coverage: float,
    max_final_wait_ms: float,
    max_backlog_ms: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    final_texts: list[str] = []
    statuses: list[str] = []
    for segment in strategy_entry["segments"]:
        summary = summaries.get(segment["segment_id"])
        wall_ms = wall_ms_from_summary(summary, float(segment["audio_duration_seconds"]))
        final_text = "" if summary is None else str(summary.get("final_text") or "")
        status = "missing" if summary is None else str(summary.get("status") or "unknown")
        final_texts.append(final_text)
        statuses.append(status)
        rows.append(
            {
                **segment,
                "status": status,
                "wall_ms": wall_ms,
                "final_text_chars": len(normalize_for_cer(final_text)),
                "error": None if summary is None else summary.get("error"),
            }
        )
    aggregate_text = "".join(final_texts)
    expected_text = str(case_entry["source_expected_text"])
    aggregate_cer = cer(expected_text, aggregate_text)
    aggregate_wer = wer(expected_text, aggregate_text)
    coverage = coverage_ratio(expected_text, aggregate_text)
    wall_values = [float(row["wall_ms"]) for row in rows if row.get("wall_ms") is not None]
    timing = serial_worker_timing(rows, float(case_entry["source_duration_seconds"]))
    warnings: list[str] = []
    if any(status not in {"ok", "no_text"} for status in statuses):
        warnings.append("存在缺失或错误的 segment 识别结果。")
    if coverage is not None and coverage < min_coverage:
        warnings.append(f"整段输出覆盖率 {coverage:.3f} 低于阈值 {min_coverage:.3f}，可能漏尾或漏段。")
    if aggregate_cer is not None and aggregate_cer > max_cer:
        warnings.append(f"整段 CER {aggregate_cer:.3f} 高于阈值 {max_cer:.3f}。")
    if timing["serial_final_wait_ms"] > max_final_wait_ms:
        warnings.append(
            f"估算停止后等待 {timing['serial_final_wait_ms']:.0f}ms 高于阈值 {max_final_wait_ms:.0f}ms。"
        )
    if timing["serial_max_lag_ms"] > max_backlog_ms:
        warnings.append(
            f"估算后台最大积压 {timing['serial_max_lag_ms']:.0f}ms 高于阈值 {max_backlog_ms:.0f}ms。"
        )
    if float(strategy_entry["overlap_seconds"]) > 0:
        warnings.append("当前聚合使用 naive 拼接；非零 overlap 可能重复文字，需要后续去重/对齐。")

    pass_candidate = not warnings
    return {
        "source_case_id": case_entry["source_case_id"],
        "strategy_id": strategy_entry["strategy_id"],
        "source_duration_seconds": case_entry["source_duration_seconds"],
        "source_expected_chars": case_entry["source_expected_chars"],
        "segment_count": strategy_entry["segment_count"],
        "max_segment_seconds": strategy_entry["max_segment_seconds"],
        "soft_text_chars": strategy_entry["soft_text_chars"],
        "overlap_seconds": strategy_entry["overlap_seconds"],
        "total_segment_audio_sec": round3(sum(float(row["audio_duration_seconds"]) for row in rows)),
        "total_model_wall_ms": round(sum(wall_values), 3) if wall_values else None,
        "max_segment_wall_ms": round(max(wall_values), 3) if wall_values else None,
        "mean_segment_wall_ms": round(statistics.fmean(wall_values), 3) if wall_values else None,
        "cer": aggregate_cer,
        "wer": aggregate_wer,
        "coverage": coverage,
        "aggregate_final_text": aggregate_text,
        "warnings_zh": warnings,
        "pass_candidate": pass_candidate,
        **timing,
        "segments": rows,
    }


def summarize_strategies(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_strategy: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        by_strategy.setdefault(str(group["strategy_id"]), []).append(group)
    summaries: list[dict[str, Any]] = []
    for strategy_id, values in sorted(by_strategy.items()):
        cer_values = [float(item["cer"]) for item in values if isinstance(item.get("cer"), (int, float))]
        coverage_values = [
            float(item["coverage"]) for item in values if isinstance(item.get("coverage"), (int, float))
        ]
        summaries.append(
            {
                "strategy_id": strategy_id,
                "case_count": len(values),
                "pass_candidate_count": sum(1 for item in values if item.get("pass_candidate")),
                "avg_cer": statistics.fmean(cer_values) if cer_values else None,
                "min_coverage": min(coverage_values) if coverage_values else None,
                "max_serial_final_wait_ms": max(float(item["serial_final_wait_ms"]) for item in values),
                "max_serial_backlog_ms": max(float(item["serial_max_lag_ms"]) for item in values),
                "max_segment_count": max(int(item["segment_count"]) for item in values),
                "total_model_wall_ms": sum(
                    float(item["total_model_wall_ms"])
                    for item in values
                    if isinstance(item.get("total_model_wall_ms"), (int, float))
                ),
            }
        )
    return summaries


def recommendation_zh(strategy_summaries: list[dict[str, Any]], groups: list[dict[str, Any]]) -> list[str]:
    messages: list[str] = []
    passing = [item for item in strategy_summaries if item["pass_candidate_count"] == item["case_count"]]
    if passing:
        best = sorted(
            passing,
            key=lambda item: (
                float(item["max_serial_final_wait_ms"]),
                float(item["max_serial_backlog_ms"]),
                int(item["max_segment_count"]),
            ),
        )[0]
        messages.append(
            f"本次小样本中 `{best['strategy_id']}` 是最稳的候选：所有 case 通过阈值，"
            f"最大停止后等待约 {best['max_serial_final_wait_ms']:.0f}ms。"
        )
    else:
        messages.append("本次没有策略在全部 case 上满足所有阈值；需要收紧切段、优化识别或扩大样本后再定默认值。")
    if any(float(group["overlap_seconds"]) > 0 for group in groups):
        messages.append("非零 overlap 的拼接需要文本去重/对齐，否则可能把重叠区域重复写入最终文本。")
    messages.append("当前结果仍是离线分段评测，不代表 macOS App 已经支持分段缓存运行时。")
    messages.append("下一步应扩大到自然长语音和更长合成压力样本，再把通过的策略转成服务侧实现 spec。")
    return messages


def write_markdown(path: Path, analysis: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    groups = analysis["groups"]
    with path.open("w", encoding="utf-8") as f:
        f.write("# Segmented Cache ASR Analysis\n\n")
        f.write("## Metric Notes\n\n")
        for key, explanation in METRIC_EXPLANATIONS_ZH.items():
            f.write(f"- `{key}`: {explanation}\n")
        f.write("\n## Strategy Summary\n\n")
        f.write(
            "| strategy | cases | pass candidates | avg CER | min coverage | max final wait ms | max backlog ms | max segments |\n"
        )
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for item in analysis["strategy_summaries"]:
            f.write(
                "| "
                + " | ".join(
                    [
                        str(item["strategy_id"]),
                        str(item["case_count"]),
                        str(item["pass_candidate_count"]),
                        "-" if item["avg_cer"] is None else f"{item['avg_cer']:.4f}",
                        "-" if item["min_coverage"] is None else f"{item['min_coverage']:.3f}",
                        f"{item['max_serial_final_wait_ms']:.1f}",
                        f"{item['max_serial_backlog_ms']:.1f}",
                        str(item["max_segment_count"]),
                    ]
                )
                + " |\n"
            )
        f.write("\n## Case Strategy Results\n\n")
        f.write(
            "| source case | strategy | segments | total model wall ms | max segment wall ms | final wait ms | backlog ms | CER | WER | coverage | status |\n"
        )
        f.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for group in groups:
            f.write(
                "| "
                + " | ".join(
                    [
                        str(group["source_case_id"]),
                        str(group["strategy_id"]),
                        str(group["segment_count"]),
                        "-" if group["total_model_wall_ms"] is None else f"{group['total_model_wall_ms']:.1f}",
                        "-" if group["max_segment_wall_ms"] is None else f"{group['max_segment_wall_ms']:.1f}",
                        f"{group['serial_final_wait_ms']:.1f}",
                        f"{group['serial_max_lag_ms']:.1f}",
                        "-" if group["cer"] is None else f"{group['cer']:.4f}",
                        "-" if group["wer"] is None else f"{group['wer']:.4f}",
                        "-" if group["coverage"] is None else f"{group['coverage']:.3f}",
                        "pass" if group["pass_candidate"] else "warn",
                    ]
                )
                + " |\n"
            )
        warnings = [
            (group["source_case_id"], group["strategy_id"], warning)
            for group in groups
            for warning in group["warnings_zh"]
        ]
        if warnings:
            f.write("\n## Warnings\n\n")
            for source_case_id, strategy_id, warning in warnings:
                f.write(f"- `{source_case_id}` / `{strategy_id}`: {warning}\n")
        f.write("\n## Recommendation\n\n")
        for item in analysis["recommendation_zh"]:
            f.write(f"- {item}\n")


def command_analyze(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    summaries = load_segment_summaries(Path(args.run_summary))
    groups: list[dict[str, Any]] = []
    for case_entry in manifest.get("cases", []):
        for strategy_entry in case_entry.get("strategies", []):
            groups.append(
                analyze_group(
                    case_entry=case_entry,
                    strategy_entry=strategy_entry,
                    summaries=summaries,
                    max_cer=args.max_cer,
                    min_coverage=args.min_coverage,
                    max_final_wait_ms=args.max_final_wait_ms,
                    max_backlog_ms=args.max_backlog_ms,
                )
            )
    strategy_summaries = summarize_strategies(groups)
    analysis = {
        "schema_version": "1.0",
        "manifest": str(args.manifest),
        "run_summary": str(args.run_summary),
        "created_epoch_ms": int(time.time() * 1000),
        "thresholds": {
            "max_cer": args.max_cer,
            "min_coverage": args.min_coverage,
            "max_final_wait_ms": args.max_final_wait_ms,
            "max_backlog_ms": args.max_backlog_ms,
        },
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "strategy_summaries": strategy_summaries,
        "groups": groups,
        "recommendation_zh": recommendation_zh(strategy_summaries, groups),
    }
    out_dir = Path(args.out_dir)
    write_json(out_dir / "analysis.json", analysis)
    write_markdown(out_dir / "analysis.md", analysis)
    print(json.dumps(analysis, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Generate segment WAVs, case JSONL, and a manifest.")
    prepare.add_argument("--source-cases", default=str(DEFAULT_SOURCE_CASES))
    prepare.add_argument("--case-id", action="append", help="Source case id to include. Repeatable.")
    prepare.add_argument("--strategy", action="append", help="name:max_segment_sec:soft_text_chars:overlap_sec")
    prepare.add_argument("--min-segment-sec", type=float, default=8.0)
    prepare.add_argument("--out-audio-dir", default=str(DEFAULT_OUT_AUDIO_DIR))
    prepare.add_argument("--out-cases", default=str(DEFAULT_OUT_CASES))
    prepare.add_argument("--out-manifest", default=str(DEFAULT_OUT_MANIFEST))
    prepare.add_argument("--dry-run", action="store_true")
    prepare.set_defaults(func=command_prepare)

    analyze = sub.add_parser("analyze", help="Analyze a run_eval.py summary using the segment manifest.")
    analyze.add_argument("--manifest", default=str(DEFAULT_OUT_MANIFEST))
    analyze.add_argument("--run-summary", required=True)
    analyze.add_argument("--out-dir", required=True)
    analyze.add_argument("--max-cer", type=float, default=0.10)
    analyze.add_argument("--min-coverage", type=float, default=0.90)
    analyze.add_argument("--max-final-wait-ms", type=float, default=5000.0)
    analyze.add_argument("--max-backlog-ms", type=float, default=10000.0)
    analyze.set_defaults(func=command_analyze)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
