#!/usr/bin/env python3
"""Analyze controlled ASR segment-budget timing results."""

from __future__ import annotations

import argparse
import json
import statistics
import unicodedata
from pathlib import Path
from typing import Any


METRIC_EXPLANATIONS_ZH = {
    "wall_ms": "墙钟耗时，单位毫秒；这里近似等于本次 final 文件级识别真实等待时间。",
    "rtf": "实时因子，等于墙钟耗时除以音频时长；小于 1 表示处理速度快于实时播放。",
    "cer": "字符错误率，越低越好；中文主要看这个。",
    "wer": "词/token 错误率，越低越好；中英混合时辅助观察英文和技术词。",
    "expected_chars": "标准答案归一化后的字符数量，可粗略代表这段音频里需要转写的文字内容量。",
    "final_chars": "模型输出归一化后的字符数量。",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def load_case_metadata(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    cases: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            obj = json.loads(stripped)
            cases[str(obj["id"])] = obj
    return cases


def normalize_for_length(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    chars: list[str] = []
    for ch in normalized:
        category = unicodedata.category(ch)
        if category.startswith("P") or category.startswith("Z") or category.startswith("C"):
            continue
        chars.append(ch)
    return "".join(chars)


def safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def slope(points: list[tuple[float, float]]) -> float | None:
    if len(points) < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - x_mean) * (y - y_mean) for x, y in points) / denom


def fmt(value: Any, digits: int = 3) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    if value is None:
        return "-"
    return str(value)


def row_from_summary(summary: dict[str, Any], case_obj: dict[str, Any] | None) -> dict[str, Any]:
    duration = float(summary.get("duration_seconds") or 0.0)
    rtf = safe_float(summary.get("rtf"))
    wall_ms = None if rtf is None else rtf * duration * 1000.0
    expected_text = str(summary.get("expected_text") or "")
    final_text = str(summary.get("final_text") or "")
    metadata = dict((case_obj or {}).get("metadata") or {})
    axis = metadata.get("segment_budget_axis") or summary.get("scenario") or "unknown"
    return {
        "case_id": summary.get("case_id"),
        "status": summary.get("status"),
        "axis": axis,
        "scenario": summary.get("scenario"),
        "duration_seconds": duration,
        "expected_chars": len(normalize_for_length(expected_text)),
        "final_chars": len(normalize_for_length(final_text)),
        "wall_ms": wall_ms,
        "rtf": rtf,
        "cer": summary.get("cer"),
        "wer": summary.get("wer"),
        "source_text_multiplier": metadata.get("source_text_multiplier"),
        "silence_pad_seconds": metadata.get("silence_pad_seconds"),
        "synthetic_note": metadata.get("synthetic_note"),
    }


def group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["axis"]), []).append(row)
    for values in groups.values():
        values.sort(key=lambda item: float(item["duration_seconds"]))
    return groups


def build_comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = group_rows(rows)
    comparisons: dict[str, Any] = {}
    for axis, values in groups.items():
        usable = [
            (float(row["duration_seconds"]), float(row["wall_ms"]))
            for row in values
            if row.get("wall_ms") is not None
        ]
        comparisons[axis] = {
            "case_count": len(values),
            "duration_to_wall_ms_slope_ms_per_audio_sec": slope(usable),
            "min_duration_seconds": min((float(r["duration_seconds"]) for r in values), default=None),
            "max_duration_seconds": max((float(r["duration_seconds"]) for r in values), default=None),
            "min_wall_ms": min((float(r["wall_ms"]) for r in values if r.get("wall_ms") is not None), default=None),
            "max_wall_ms": max((float(r["wall_ms"]) for r in values if r.get("wall_ms") is not None), default=None),
        }
    text_points = [
        (float(row["expected_chars"]), float(row["wall_ms"]))
        for row in rows
        if row.get("wall_ms") is not None
    ]
    duration_points = [
        (float(row["duration_seconds"]), float(row["wall_ms"]))
        for row in rows
        if row.get("wall_ms") is not None
    ]
    comparisons["overall"] = {
        "text_length_to_wall_ms_slope_ms_per_char": slope(text_points),
        "duration_to_wall_ms_slope_ms_per_audio_sec": slope(duration_points),
    }
    return comparisons


def recommendation_zh(comparisons: dict[str, Any]) -> list[str]:
    same_text_slope = comparisons.get("same_text_longer_audio", {}).get(
        "duration_to_wall_ms_slope_ms_per_audio_sec"
    )
    silence_slope = comparisons.get("silence_duration_only", {}).get(
        "duration_to_wall_ms_slope_ms_per_audio_sec"
    )
    repeat_slope = comparisons.get("more_text_longer_audio", {}).get(
        "duration_to_wall_ms_slope_ms_per_audio_sec"
    )
    messages: list[str] = []
    if same_text_slope is not None and same_text_slope > 5:
        messages.append("同样文字后面补静音仍然会增加处理耗时，所以不能只按已转写文字长度切段。")
    if silence_slope is not None and silence_slope > 5:
        messages.append("纯静音随时长变长也有可见成本，说明音频时长本身就是必须受控的资源。")
    if repeat_slope is not None and same_text_slope is not None and repeat_slope > same_text_slope * 1.2:
        messages.append("重复内容组的耗时增长高于补静音组，说明文字/内容量也会带来额外成本。")
    messages.append(
        "建议后续分段采用混合预算：硬性音频时长上限 + 软性文字长度上限 + 静音/标点边界优先切分，而不是只用两分钟或只用字数。"
    )
    messages.append(
        "这组是 compute-isolation pilot；最终产品阈值还需要至少重复跑 2-3 次，并加入自然长语音样本。"
    )
    return messages


def quality_warnings_zh(rows: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for row in rows:
        expected_chars = int(row.get("expected_chars") or 0)
        final_chars = int(row.get("final_chars") or 0)
        cer = row.get("cer")
        if expected_chars > 0 and final_chars / max(1, expected_chars) < 0.9:
            warnings.append(
                f"{row['case_id']} 输出覆盖率只有 {final_chars}/{expected_chars}，"
                "说明这次 final 识别没有完整覆盖标准答案。"
            )
        if isinstance(cer, (int, float)) and float(cer) > 0.10:
            warnings.append(
                f"{row['case_id']} CER={float(cer):.4f}，明显高于可接受的普通听写水平。"
            )
    if warnings:
        warnings.append(
            "这些警告优先级高于耗时指标：一个很快但漏掉末尾内容的 final，不能作为可用的长段重算策略。"
        )
    return warnings


def write_markdown(path: Path, analysis: dict[str, Any]) -> None:
    rows = analysis["rows"]
    comparisons = analysis["comparisons"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("# Segment Budget ASR Analysis\n\n")
        f.write("## Metric Notes\n\n")
        for key, explanation in METRIC_EXPLANATIONS_ZH.items():
            f.write(f"- `{key}`: {explanation}\n")
        f.write("\n## Case Results\n\n")
        f.write("| case | axis | audio sec | expected chars | final chars | wall ms | RTF | CER | WER | status |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for row in sorted(rows, key=lambda item: (str(item["axis"]), float(item["duration_seconds"]))):
            f.write(
                "| "
                + " | ".join(
                    [
                        str(row["case_id"]),
                        str(row["axis"]),
                        fmt(row["duration_seconds"]),
                        fmt(row["expected_chars"], 0),
                        fmt(row["final_chars"], 0),
                        fmt(row["wall_ms"], 1),
                        fmt(row["rtf"]),
                        fmt(row["cer"]),
                        fmt(row["wer"]),
                        str(row["status"]),
                    ]
                )
                + " |\n"
            )
        f.write("\n## Comparisons\n\n")
        for key, value in comparisons.items():
            f.write(f"- `{key}`: {json.dumps(value, ensure_ascii=False, sort_keys=True)}\n")
        if analysis.get("quality_warnings_zh"):
            f.write("\n## Quality Warnings\n\n")
            for item in analysis["quality_warnings_zh"]:
                f.write(f"- {item}\n")
        f.write("\n## Recommendation\n\n")
        for item in analysis["recommendation_zh"]:
            f.write(f"- {item}\n")


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    aggregate = load_json(Path(args.summary))
    case_metadata = load_case_metadata(Path(args.cases) if args.cases else None)
    all_rows = [
        row_from_summary(case_summary, case_metadata.get(str(case_summary.get("case_id"))))
        for case_summary in aggregate.get("cases", [])
    ]
    warmup_rows = [row for row in all_rows if row.get("axis") == "warmup"]
    rows = [row for row in all_rows if row.get("axis") != "warmup"]
    comparisons = build_comparisons(rows)
    quality_warnings = quality_warnings_zh(rows)
    recommendation = quality_warnings + recommendation_zh(comparisons)
    return {
        "summary": str(args.summary),
        "cases": str(args.cases) if args.cases else None,
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "warmup_rows_excluded": warmup_rows,
        "rows": rows,
        "comparisons": comparisons,
        "quality_warnings_zh": quality_warnings,
        "recommendation_zh": recommendation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="Path to run_eval aggregate summary.json")
    parser.add_argument("--cases", default="eval/asr_streaming/cases.segment_budget.local.jsonl")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = analyze(args)
    out_dir = Path(args.out_dir)
    write_json(out_dir / "analysis.json", result)
    write_markdown(out_dir / "analysis.md", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
