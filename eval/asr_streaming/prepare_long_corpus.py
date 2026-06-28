#!/usr/bin/env python3
"""Prepare long-dictation ASR cases from a license-tracked manifest.

The script never downloads media. It converts local source files listed in the
manifest into 16 kHz mono int16 WAV files and writes a JSONL case file for
items with transcripts.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / "eval" / "asr_streaming"


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be a JSON object")
    if payload.get("schema_version") != "1.0":
        raise ValueError("manifest schema_version must be 1.0")
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest items must be a list")
    return payload


def resolve_repo_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def relative_to_eval(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(EVAL_ROOT.resolve()))
    except ValueError:
        return str(path)


def validate_item(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["id", "source_type", "purpose", "language", "output_audio"]:
        if not str(item.get(key, "")).strip():
            errors.append(f"missing {key}")
    if not item.get("enabled", False):
        return errors
    if item.get("purpose") == "metric" and not item.get("metric_bearing"):
        errors.append("metric purpose requires metric_bearing=true")
    if item.get("metric_bearing") and not (
        str(item.get("transcript_text") or "").strip() or str(item.get("transcript_path") or "").strip()
    ):
        errors.append("metric-bearing item requires transcript_text or transcript_path")
    if item.get("source_type") == "public_media_candidate" and item.get("purpose") == "metric":
        if str(item.get("license") or "").lower().startswith("todo"):
            errors.append("public metric media requires verified license")
    return errors


def transcript_for_item(item: dict[str, Any]) -> str:
    direct = str(item.get("transcript_text") or "").strip()
    if direct:
        return direct
    transcript_path = resolve_repo_path(item.get("transcript_path"))
    if transcript_path and transcript_path.exists():
        return transcript_path.read_text(encoding="utf-8").strip()
    return ""


def ffmpeg_convert(src: Path, dst: Path, *, force: bool) -> None:
    if dst.exists() and not force:
        return
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to prepare media. Install ffmpeg or use dry-run.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if force else "-n",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    subprocess.run(command, check=True)


def build_synthetic_repetition(src: Path, dst: Path, *, target_seconds: float, force: bool) -> tuple[int, float]:
    with wave.open(str(src), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        frames = reader.readframes(reader.getnframes())
        frame_count = reader.getnframes()

    if channels != 1 or sample_width != 2 or sample_rate != 16000:
        raise ValueError(f"synthetic source must be 16 kHz mono int16 WAV: {src}")
    if frame_count <= 0:
        raise ValueError(f"synthetic source has no audio frames: {src}")

    repeat_count = max(1, math.ceil((target_seconds * sample_rate) / frame_count))
    if dst.exists() and not force:
        with wave.open(str(dst), "rb") as existing:
            duration_seconds = existing.getnframes() / float(existing.getframerate())
        return repeat_count, duration_seconds

    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(sample_width)
        writer.setframerate(sample_rate)
        for _ in range(repeat_count):
            writer.writeframes(frames)
    duration_seconds = (frame_count * repeat_count) / float(sample_rate)
    return repeat_count, duration_seconds


def item_is_selected(item: dict[str, Any], selected_ids: set[str]) -> bool:
    item_id = str(item.get("id", ""))
    if selected_ids:
        return item_id in selected_ids
    return bool(item.get("enabled", False))


def command_run(args: argparse.Namespace) -> int:
    manifest_path = resolve_repo_path(args.manifest)
    if manifest_path is None:
        raise ValueError("--manifest is required")
    manifest = load_manifest(manifest_path)
    selected_ids = set(args.only_id or [])
    cases: list[dict[str, Any]] = []
    prepared_count = 0
    skipped: list[dict[str, str]] = []
    validation_errors: list[str] = []

    for raw_item in manifest["items"]:
        if not isinstance(raw_item, dict):
            validation_errors.append("manifest item must be an object")
            continue
        item_id = str(raw_item.get("id", "<missing-id>"))
        errors = validate_item(raw_item)
        if errors:
            validation_errors.extend(f"{item_id}: {error}" for error in errors)
        if not item_is_selected(raw_item, selected_ids):
            skipped.append({"id": item_id, "reason": "disabled_or_not_selected"})
            continue

        src = resolve_repo_path(raw_item.get("local_source_path"))
        dst = resolve_repo_path(raw_item.get("output_audio"))
        if dst is None:
            skipped.append({"id": item_id, "reason": "missing_output_audio"})
            continue
        if src is None:
            skipped.append({"id": item_id, "reason": "missing_local_source_path"})
            continue
        if not src.exists():
            skipped.append({"id": item_id, "reason": f"missing_local_source_path:{src}"})
            continue

        text = transcript_for_item(raw_item)
        if raw_item.get("metric_bearing") and not text:
            skipped.append({"id": item_id, "reason": "missing_transcript"})
            continue

        synthetic_repeat_count = None
        synthetic_duration_seconds = None
        if raw_item.get("source_type") == "synthetic_repetition":
            target_seconds = float(raw_item.get("repeat_to_min_duration_sec") or raw_item.get("duration_target_sec") or 0)
            if target_seconds <= 0:
                skipped.append({"id": item_id, "reason": "missing_repeat_to_min_duration_sec"})
                continue
            if args.dry_run:
                prepared_path = dst if dst.exists() else src
                if src.exists():
                    with wave.open(str(src), "rb") as reader:
                        source_duration = reader.getnframes() / float(reader.getframerate())
                    synthetic_repeat_count = max(1, math.ceil(target_seconds / source_duration))
                    synthetic_duration_seconds = source_duration * synthetic_repeat_count
            else:
                synthetic_repeat_count, synthetic_duration_seconds = build_synthetic_repetition(
                    src,
                    dst,
                    target_seconds=target_seconds,
                    force=args.force,
                )
                prepared_path = dst
                prepared_count += 1
        elif args.dry_run:
            prepared_path = dst if dst.exists() else src
        else:
            if src.resolve() != dst.resolve():
                ffmpeg_convert(src, dst, force=args.force)
            prepared_path = dst
            prepared_count += 1

        if text:
            if synthetic_repeat_count is not None and synthetic_repeat_count > 1:
                text = " ".join([text] * synthetic_repeat_count)
            cases.append(
                {
                    "id": item_id,
                    "audio": relative_to_eval(prepared_path),
                    "text": text,
                    "lang": str(raw_item.get("language", "unknown")),
                    "scenario": str(raw_item.get("scenario", raw_item.get("purpose", "long_dictation"))),
                    "metadata": {
                        "source_type": raw_item.get("source_type"),
                        "purpose": raw_item.get("purpose"),
                        "metric_bearing": bool(raw_item.get("metric_bearing")),
                        "license": raw_item.get("license"),
                        "source_url": raw_item.get("source_url"),
                        "duration_target_sec": raw_item.get("duration_target_sec"),
                        "synthetic_repeat_count": synthetic_repeat_count,
                        "synthetic_duration_seconds": synthetic_duration_seconds,
                    },
                }
            )

    if validation_errors:
        for error in validation_errors:
            print(f"manifest warning: {error}", file=sys.stderr)

    out_cases = resolve_repo_path(args.out_cases)
    if out_cases is None:
        raise ValueError("--out-cases is required")
    if not args.dry_run:
        out_cases.parent.mkdir(parents=True, exist_ok=True)
        with out_cases.open("w", encoding="utf-8") as handle:
            for case in cases:
                handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "schema_version": "1.0",
        "manifest": str(manifest_path),
        "out_cases": str(out_cases),
        "dry_run": bool(args.dry_run),
        "selected_count": len(cases),
        "prepared_count": prepared_count,
        "skipped": skipped,
        "warnings": validation_errors,
        "metric_explanations_zh": manifest.get("metric_explanations_zh", {}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not validation_errors or args.allow_warnings else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="eval/asr_streaming/long_corpus_manifest.json")
    parser.add_argument("--out-cases", default="eval/asr_streaming/cases.long_prepared.local.jsonl")
    parser.add_argument("--only-id", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-warnings", action="store_true", help="Return success even when disabled candidate placeholders have warnings.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return command_run(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
