#!/usr/bin/env python3
"""Prepare controlled WAV cases for ASR segment-budget timing tests."""

from __future__ import annotations

import argparse
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_CASES = Path("eval/asr_streaming/cases.local.jsonl")
DEFAULT_SOURCE_CASE_ID = "long_120_001"
DEFAULT_OUT_DIR = Path("eval/asr_streaming/audio/segment_budget")
DEFAULT_OUT_CASES = Path("eval/asr_streaming/cases.segment_budget.local.jsonl")


@dataclass(frozen=True)
class SourceCase:
    case_id: str
    audio_path: Path
    text: str
    lang: str
    scenario: str


@dataclass(frozen=True)
class WavData:
    frames: bytes
    sample_rate: int
    channels: int
    sample_width: int

    @property
    def frame_count(self) -> int:
        return len(self.frames) // (self.channels * self.sample_width)

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / float(self.sample_rate)


def load_source_cases(path: Path) -> dict[str, SourceCase]:
    cases: dict[str, SourceCase] = {}
    base = path.parent
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            obj = json.loads(stripped)
            audio_path = Path(str(obj["audio"]))
            if not audio_path.is_absolute():
                audio_path = base / audio_path
            case = SourceCase(
                case_id=str(obj["id"]),
                audio_path=audio_path,
                text=str(obj["text"]),
                lang=str(obj["lang"]),
                scenario=str(obj["scenario"]),
            )
            if case.case_id in cases:
                raise ValueError(f"{path}:{lineno}: duplicate case id {case.case_id}")
            cases[case.case_id] = case
    return cases


def read_wav(path: Path) -> WavData:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if channels != 1 or sample_width != 2 or sample_rate != 16000:
        raise ValueError(
            f"{path} must be 16 kHz mono signed 16-bit PCM WAV; "
            f"got {sample_rate} Hz, {channels} channels, sample width {sample_width}"
        )
    return WavData(
        frames=frames,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
    )


def write_wav(path: Path, wav_data: WavData, frames: bytes) -> float:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(wav_data.channels)
        wav.setsampwidth(wav_data.sample_width)
        wav.setframerate(wav_data.sample_rate)
        wav.writeframes(frames)
    frame_count = len(frames) // (wav_data.channels * wav_data.sample_width)
    return frame_count / float(wav_data.sample_rate)


def silence_frames(wav_data: WavData, seconds: float) -> bytes:
    frame_count = max(0, int(round(seconds * wav_data.sample_rate)))
    return b"\x00" * frame_count * wav_data.channels * wav_data.sample_width


def rel_to_cases(path: Path, cases_path: Path) -> str:
    return str(path.relative_to(cases_path.parent))


def round_seconds(seconds: float) -> int:
    return int(round(seconds))


def build_record(
    *,
    case_id: str,
    audio_path: Path,
    cases_path: Path,
    text: str,
    lang: str,
    scenario: str,
    duration_seconds: float,
    source: SourceCase,
    axis: str,
    source_text_multiplier: int,
    silence_pad_seconds: float,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "audio": rel_to_cases(audio_path, cases_path),
        "text": text,
        "lang": lang,
        "scenario": scenario,
        "metadata": {
            "purpose": "segment_budget_compute_probe",
            "metric_bearing": False,
            "source_case_id": source.case_id,
            "source_scenario": source.scenario,
            "segment_budget_axis": axis,
            "duration_seconds": round(duration_seconds, 3),
            "expected_text_chars": len(text),
            "source_text_multiplier": source_text_multiplier,
            "silence_pad_seconds": round(silence_pad_seconds, 3),
            "synthetic_note": (
                "Controlled synthetic case for compute isolation only; "
                "do not use as natural long-dictation UX quality evidence."
            ),
        },
    }


def prepare_cases(args: argparse.Namespace) -> list[dict[str, Any]]:
    source_cases = load_source_cases(Path(args.source_cases))
    if args.source_case_id not in source_cases:
        available = ", ".join(sorted(source_cases))
        raise ValueError(f"source case {args.source_case_id!r} not found; available: {available}")
    source = source_cases[args.source_case_id]
    wav_data = read_wav(source.audio_path)
    out_dir = Path(args.out_dir)
    out_cases = Path(args.out_cases)
    base_duration = wav_data.duration_seconds
    planned: list[dict[str, Any]] = []

    if not args.no_warmup:
        warmup_id = f"budget_warmup_{round_seconds(base_duration)}s"
        warmup_path = out_dir / f"{warmup_id}.wav"
        if not args.dry_run:
            duration = write_wav(warmup_path, wav_data, wav_data.frames)
        else:
            duration = base_duration
        planned.append(
            build_record(
                case_id=warmup_id,
                audio_path=warmup_path,
                cases_path=out_cases,
                text=source.text,
                lang=source.lang,
                scenario="segment_budget_warmup",
                duration_seconds=duration,
                source=source,
                axis="warmup",
                source_text_multiplier=1,
                silence_pad_seconds=0.0,
            )
        )

    base_id = f"budget_same_text_base_{round_seconds(base_duration)}s"
    base_path = out_dir / f"{base_id}.wav"
    if not args.dry_run:
        duration = write_wav(base_path, wav_data, wav_data.frames)
    else:
        duration = base_duration
    planned.append(
        build_record(
            case_id=base_id,
            audio_path=base_path,
            cases_path=out_cases,
            text=source.text,
            lang=source.lang,
            scenario="segment_budget_same_text_base",
            duration_seconds=duration,
            source=source,
            axis="same_text_base",
            source_text_multiplier=1,
            silence_pad_seconds=0.0,
        )
    )

    for target_sec in sorted(set(float(v) for v in args.pad_targets)):
        if target_sec <= base_duration:
            continue
        case_id = f"budget_same_text_pad_{round_seconds(target_sec)}s"
        path = out_dir / f"{case_id}.wav"
        pad_sec = target_sec - base_duration
        frames = wav_data.frames + silence_frames(wav_data, pad_sec)
        if not args.dry_run:
            duration = write_wav(path, wav_data, frames)
        else:
            duration = target_sec
        planned.append(
            build_record(
                case_id=case_id,
                audio_path=path,
                cases_path=out_cases,
                text=source.text,
                lang=source.lang,
                scenario="segment_budget_same_text_padded",
                duration_seconds=duration,
                source=source,
                axis="same_text_longer_audio",
                source_text_multiplier=1,
                silence_pad_seconds=pad_sec,
            )
        )

    silence_durations = [base_duration, *(float(v) for v in args.silence_durations)]
    for silence_sec in sorted({round(v, 3) for v in silence_durations if v > 0}):
        case_id = f"budget_silence_{round_seconds(silence_sec)}s"
        path = out_dir / f"{case_id}.wav"
        frames = silence_frames(wav_data, silence_sec)
        if not args.dry_run:
            duration = write_wav(path, wav_data, frames)
        else:
            duration = silence_sec
        planned.append(
            build_record(
                case_id=case_id,
                audio_path=path,
                cases_path=out_cases,
                text="",
                lang=source.lang,
                scenario="segment_budget_silence_only",
                duration_seconds=duration,
                source=source,
                axis="silence_duration_only",
                source_text_multiplier=0,
                silence_pad_seconds=duration,
            )
        )

    for repeat_count in sorted(set(int(v) for v in args.repeat_counts)):
        if repeat_count <= 1:
            continue
        case_id = f"budget_repeat_{repeat_count}x_{round_seconds(base_duration * repeat_count)}s"
        path = out_dir / f"{case_id}.wav"
        frames = wav_data.frames * repeat_count
        text = " ".join(source.text for _ in range(repeat_count))
        if not args.dry_run:
            duration = write_wav(path, wav_data, frames)
        else:
            duration = base_duration * repeat_count
        planned.append(
            build_record(
                case_id=case_id,
                audio_path=path,
                cases_path=out_cases,
                text=text,
                lang=source.lang,
                scenario="segment_budget_repeated_content",
                duration_seconds=duration,
                source=source,
                axis="more_text_longer_audio",
                source_text_multiplier=repeat_count,
                silence_pad_seconds=0.0,
            )
        )

    if not args.dry_run:
        out_cases.parent.mkdir(parents=True, exist_ok=True)
        with out_cases.open("w", encoding="utf-8") as f:
            for record in planned:
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cases", default=str(DEFAULT_SOURCE_CASES))
    parser.add_argument("--source-case-id", default=DEFAULT_SOURCE_CASE_ID)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--out-cases", default=str(DEFAULT_OUT_CASES))
    parser.add_argument("--pad-targets", type=float, nargs="+", default=[60.0, 120.0])
    parser.add_argument("--silence-durations", type=float, nargs="+", default=[60.0, 120.0])
    parser.add_argument("--repeat-counts", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = prepare_cases(args)
    print(
        json.dumps(
            {
                "dry_run": bool(args.dry_run),
                "case_count": len(records),
                "out_cases": args.out_cases,
                "cases": [
                    {
                        "id": item["id"],
                        "audio": item["audio"],
                        "scenario": item["scenario"],
                        "duration_seconds": item["metadata"]["duration_seconds"],
                        "expected_text_chars": item["metadata"]["expected_text_chars"],
                        "axis": item["metadata"]["segment_budget_axis"],
                    }
                    for item in records
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
