#!/usr/bin/env python3
"""Guided local recording tool for ASR evaluation cases."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = REPO_ROOT / "eval/asr_streaming/cases.local.jsonl"
DEFAULT_TEMPLATE = REPO_ROOT / "eval/asr_streaming/cases.local.template.jsonl"
DEFAULT_OUT_DIR = REPO_ROOT / "eval/asr_streaming/audio"
DEFAULT_PILOT_COUNT = 10
DEFAULT_AUDIO_DEVICE = ":0"


@dataclass(frozen=True)
class RecordingCase:
    case_id: str
    audio: str
    text: str
    lang: str
    scenario: str
    raw: dict[str, Any]


def load_cases(path: Path) -> list[RecordingCase]:
    cases: list[RecordingCase] = []
    required = {"id", "audio", "text", "lang", "scenario"}
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            missing = sorted(required - set(obj))
            if missing:
                raise ValueError(f"{path}:{lineno}: missing keys: {', '.join(missing)}")
            cases.append(
                RecordingCase(
                    case_id=str(obj["id"]),
                    audio=str(obj["audio"]),
                    text=str(obj["text"]),
                    lang=str(obj["lang"]),
                    scenario=str(obj["scenario"]),
                    raw=obj,
                )
            )
    if not cases:
        raise ValueError(f"{path}: no cases found")
    ids = [c.case_id for c in cases]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"{path}: duplicate case ids: {', '.join(duplicates)}")
    return cases


def ensure_cases_file(cases_path: Path, template_path: Path, pilot_count: int, reset: bool) -> None:
    if cases_path.exists() and not reset:
        return
    if not template_path.exists():
        raise FileNotFoundError(f"template not found: {template_path}")
    lines = [line for line in template_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < pilot_count:
        raise ValueError(f"template has only {len(lines)} cases, requested {pilot_count}")
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    cases_path.write_text("\n".join(lines[:pilot_count]) + "\n", encoding="utf-8")
    action = "reset" if reset else "created"
    print(f"{action} {cases_path} from first {pilot_count} template cases")


def resolve_ffmpeg(explicit: str | None) -> str:
    if explicit:
        return explicit
    path = shutil.which("ffmpeg")
    if path:
        return path
    common = Path("/opt/homebrew/bin/ffmpeg")
    if common.exists():
        return str(common)
    raise FileNotFoundError("ffmpeg not found. Install it with Homebrew or pass --ffmpeg /path/to/ffmpeg.")


def list_devices(ffmpeg: str) -> int:
    cmd = [ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    printed = False
    for line in result.stdout.splitlines():
        if "AVFoundation video devices:" in line or "AVFoundation audio devices:" in line:
            print(line)
            printed = True
            continue
        if "] [" in line and "AVFoundation" in line:
            print(line)
            printed = True
    if not printed:
        print(result.stdout.rstrip())
    return 0


def validate_wav(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "file not found"
    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
    except Exception as exc:
        return False, f"not a readable WAV: {exc}"
    duration = frames / float(sample_rate) if sample_rate else 0.0
    if channels != 1 or sample_width != 2 or sample_rate != 16000:
        return (
            False,
            f"expected 16 kHz mono int16 WAV, got {sample_rate} Hz, {channels} channel(s), sample width {sample_width}",
        )
    if duration < 0.2:
        return False, f"recording too short: {duration:.2f}s"
    return True, f"{duration:.2f}s, 16 kHz mono int16 WAV"


def ffmpeg_record_command(ffmpeg: str, audio_device: str, output_path: Path) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "avfoundation",
        "-i",
        audio_device,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        str(output_path),
    ]


def record_one(ffmpeg: str, audio_device: str, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp.wav")
    if tmp_path.exists():
        tmp_path.unlink()
    cmd = ffmpeg_record_command(ffmpeg, audio_device, tmp_path)
    print("Recording... press Enter to stop.")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.4)
    if proc.poll() is not None:
        _, stderr = proc.communicate()
        print("ffmpeg failed to start recording.")
        print(stderr.strip())
        print_microphone_help()
        return False
    input()
    try:
        if proc.stdin:
            proc.stdin.write("q\n")
            proc.stdin.flush()
    except BrokenPipeError:
        pass
    try:
        _, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate()
    if proc.returncode not in (0, 255):
        print("ffmpeg recording failed.")
        if stderr.strip():
            print(stderr.strip())
        print_microphone_help()
        tmp_path.unlink(missing_ok=True)
        return False
    ok, message = validate_wav(tmp_path)
    if not ok:
        print(f"Invalid recording: {message}")
        if stderr.strip():
            print(stderr.strip())
        tmp_path.unlink(missing_ok=True)
        return False
    tmp_path.replace(output_path)
    print(f"Saved {output_path} ({message})")
    return True


def print_microphone_help() -> None:
    print()
    print("If macOS blocked microphone access, grant permission to the terminal app you used:")
    print("System Settings -> Privacy & Security -> Microphone")
    print("Then rerun: bash scripts/record_asr_cases.sh")
    print("To inspect devices: bash scripts/record_asr_cases.sh --list-devices")


def prompt_choice(prompt: str, allowed: set[str], default: str) -> str:
    while True:
        raw = input(prompt).strip().lower()
        choice = raw or default
        if choice in allowed:
            return choice
        print(f"Invalid choice: {raw}")


def print_case_header(index: int, total: int, case: RecordingCase, output_path: Path) -> None:
    print()
    print("=" * 72)
    print(f"[{index}/{total}] {case.case_id}  lang={case.lang}  scenario={case.scenario}")
    print(f"Output: {output_path}")
    print("-" * 72)
    print(case.text)
    print("=" * 72)


def run_interactive(args: argparse.Namespace) -> int:
    ffmpeg = resolve_ffmpeg(args.ffmpeg)
    if args.list_devices:
        return list_devices(ffmpeg)
    ensure_cases_file(Path(args.cases), Path(args.template), args.pilot_count, args.reset_cases)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases(Path(args.cases))
    if args.dry_run:
        print(f"ffmpeg: {ffmpeg}")
        print(f"audio device: {args.audio_device}")
        print(f"cases: {Path(args.cases)} ({len(cases)} cases)")
        print(f"output dir: {out_dir}")
        for index, case in enumerate(cases, start=1):
            print(f"{index:02d}. {case.case_id} -> {out_dir / (case.case_id + '.wav')}")
        return 0

    print("LocalVoiceInput ASR recording tool")
    print(f"Cases: {Path(args.cases)}")
    print(f"Output: {out_dir}")
    print(f"Audio device: {args.audio_device}")
    print("Controls: Enter=start/stop, s=skip, r=rerecord existing, l=list devices, q=quit")

    recorded = 0
    skipped = 0
    for index, case in enumerate(cases, start=1):
        output_path = out_dir / f"{case.case_id}.wav"
        print_case_header(index, len(cases), case, output_path)
        exists = output_path.exists()
        if exists:
            ok, message = validate_wav(output_path)
            print(f"Existing recording: {'valid' if ok else 'invalid'} ({message})")
            choice = prompt_choice("[Enter] keep/skip, r rerecord, l list devices, q quit: ", {"", "r", "l", "q"}, "")
            if choice == "q":
                break
            if choice == "l":
                list_devices(ffmpeg)
                choice = prompt_choice("[Enter] keep/skip, r rerecord, q quit: ", {"", "r", "q"}, "")
                if choice == "q":
                    break
            if choice != "r":
                skipped += 1
                continue
        else:
            choice = prompt_choice("[Enter] start recording, s skip, l list devices, q quit: ", {"", "s", "l", "q"}, "")
            if choice == "q":
                break
            if choice == "s":
                skipped += 1
                continue
            if choice == "l":
                list_devices(ffmpeg)
                choice = prompt_choice("[Enter] start recording, s skip, q quit: ", {"", "s", "q"}, "")
                if choice == "q":
                    break
                if choice == "s":
                    skipped += 1
                    continue
        if record_one(ffmpeg, args.audio_device, output_path):
            recorded += 1
        else:
            retry = prompt_choice("Recording failed. r retry, s skip, q quit: ", {"r", "s", "q"}, "r")
            if retry == "q":
                break
            if retry == "r" and record_one(ffmpeg, args.audio_device, output_path):
                recorded += 1
            else:
                skipped += 1
    print()
    print(f"Done. recorded={recorded}, skipped={skipped}")
    print("Next validation command:")
    print(f"python3 eval/asr_streaming/run_eval.py validate-cases --cases {Path(args.cases)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Case JSONL path.")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Template JSONL path.")
    parser.add_argument("--pilot-count", type=int, default=DEFAULT_PILOT_COUNT, help="Cases copied from template when cases file is missing.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for recorded WAV files.")
    parser.add_argument("--audio-device", default=DEFAULT_AUDIO_DEVICE, help='ffmpeg avfoundation input, default ":0" for audio device 0.')
    parser.add_argument("--ffmpeg", default=None, help="Path to ffmpeg.")
    parser.add_argument("--list-devices", action="store_true", help="List avfoundation capture devices and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare files and print planned recordings without recording.")
    parser.add_argument("--reset-cases", action="store_true", help="Regenerate cases file from the template pilot set.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_interactive(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
