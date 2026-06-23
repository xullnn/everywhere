#!/usr/bin/env python3
"""Gate local ASR backends for microphone-style realtime streaming behavior.

This script is intentionally stricter than run_eval.py. File-level ASR adapters
can be useful for final quality comparison, but they do not satisfy the
LocalVoiceInput MVP unless they emit partial text while audio is still being
sent and only finalize after user stop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_eval import (  # noqa: E402
    DEFAULT_CHUNK_MS,
    DEFAULT_FUNASR_CHUNK_INTERVAL,
    DEFAULT_FUNASR_CHUNK_SIZE,
    DEFAULT_MIN_COMPLETE_TEXT_RATIO,
    METRIC_EXPLANATIONS_ZH,
    EvalCase,
    WavAudio,
    append_jsonl,
    build_result_summary,
    char_length_ratio,
    classify_funasr_event,
    load_cases,
    load_model_metadata,
    monotonic_ms,
    now_ms,
    partial_rewrite_rate,
    read_wav_16k_mono_int16,
    select_funasr_transcript,
    write_json,
)


GATE_SCHEMA_VERSION = "1.0"

GATE_METRIC_EXPLANATIONS_ZH: dict[str, str] = {
    **METRIC_EXPLANATIONS_ZH,
    "realtime_gate_passed": "是否通过实时语音输入集成门槛。true 表示该 case 满足边说边出 partial、用户停止后出 final、延迟和覆盖率达标等硬条件。",
    "gate_fail_reasons": "未通过实时 gate 的具体原因列表。用于把准确率问题、延迟问题和不支持真流式的问题分开看。",
    "chunk_ms": "模拟麦克风输入时每个 PCM 分块覆盖的音频时长，单位毫秒。",
    "input_realtime_pacing": "是否按真实音频时间 sleep 发送分块。true 更接近真实麦克风；false 只用于快速诊断协议逻辑。",
    "input_finished_offset_ms": "最后一个音频分块发送完成的本地相对时间，近似等于用户停止录音前的输入持续时间。",
    "partial_before_stop_count": "用户停止录音前已经收到的 partial 数量。实时浮窗体验要求该值大于 0。",
    "final_after_stop_count": "用户停止录音后收到的 final/offline 事件数量。中途 offline segment 不等于整段会话最终结果。",
    "first_partial_audio_lag_ms": "从开始推送音频到首个 partial 到达的时间。这里使用本地接收时间近似，越低越好。",
    "partial_cadence_ms": "相邻 partial 到达间隔的平均值，单位毫秒，用于观察浮窗更新密度。",
    "partial_coverage_ratio": "最后/聚合 partial 的归一化字符长度与标准答案长度之比，用于观察录音过程中实时文本覆盖度。",
    "final_coverage_ratio": "最终文本的归一化字符长度与标准答案长度之比。过低说明 final 疑似不完整或严重漏识别。",
    "stable_final_after_stop": "停止输入后是否得到稳定 final，且没有 late partial 出现在 final 之后。",
    "partial_after_final": "是否存在 final 之后又到达的 partial。true 表示事件顺序不稳定，不能直接接入 App 会话状态机。",
}


def mean_number(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    return statistics.mean(numbers) if numbers else None


def summarize_partial_cadence(partial_events: list[dict[str, Any]]) -> float | None:
    offsets = [float(e["recv_offset_ms"]) for e in partial_events if isinstance(e.get("recv_offset_ms"), (int, float))]
    if len(offsets) < 2:
        return None
    deltas = [offsets[i] - offsets[i - 1] for i in range(1, len(offsets))]
    positive = [delta for delta in deltas if delta >= 0]
    return statistics.mean(positive) if positive else None


def evaluate_realtime_gate(
    *,
    summary: dict[str, Any],
    events: list[dict[str, Any]],
    expected_text: str,
    input_finished_offset_ms: float,
    chunk_ms: int,
    realtime: bool,
    max_first_partial_ms: float,
    max_final_latency_ms: float,
    min_partial_events: int,
    min_final_coverage_ratio: float,
    max_rtf: float,
    fail_on_suspect_final: bool,
) -> dict[str, Any]:
    partial_events = [e for e in events if e.get("kind") == "partial" and e.get("text")]
    final_events = [e for e in events if e.get("kind") == "final" and e.get("text")]
    partials_before_stop = [
        e
        for e in partial_events
        if isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) <= input_finished_offset_ms
    ]
    finals_after_stop = [
        e
        for e in final_events
        if isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) >= input_finished_offset_ms
    ]
    fail_reasons: list[str] = []

    first_partial_ms = summary.get("first_partial_ms")
    final_latency_ms = summary.get("final_latency_ms")
    final_coverage_ratio = char_length_ratio(str(summary.get("final_text", "")), expected_text)
    partial_source = str(summary.get("online_text") or summary.get("last_partial_text") or "")
    partial_coverage_ratio = char_length_ratio(partial_source, expected_text)
    partial_after_final = bool(summary.get("partial_after_final"))
    stable_final_after_stop = bool(finals_after_stop) and not partial_after_final

    if len(partial_events) < min_partial_events:
        fail_reasons.append("no_or_too_few_partial_events")
    if not partials_before_stop:
        fail_reasons.append("no_partial_before_user_stop")
    if not isinstance(first_partial_ms, (int, float)):
        fail_reasons.append("missing_first_partial_latency")
    elif float(first_partial_ms) > max_first_partial_ms:
        fail_reasons.append("first_partial_too_slow")
    if not str(summary.get("final_text", "")).strip():
        fail_reasons.append("missing_final_text")
    if not finals_after_stop:
        fail_reasons.append("no_final_after_user_stop")
    if not isinstance(final_latency_ms, (int, float)):
        fail_reasons.append("missing_final_latency")
    elif float(final_latency_ms) > max_final_latency_ms:
        fail_reasons.append("final_latency_too_slow")
    if final_coverage_ratio is not None and final_coverage_ratio < min_final_coverage_ratio:
        fail_reasons.append("final_coverage_too_low")
    if partial_after_final:
        fail_reasons.append("partial_after_final")
    if isinstance(summary.get("rtf"), (int, float)) and float(summary["rtf"]) > max_rtf:
        fail_reasons.append("rtf_too_high")
    if fail_on_suspect_final and bool(summary.get("suspect_incomplete_final")):
        fail_reasons.append("suspect_incomplete_final")

    return {
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "gate_adapter_kind": "true_streaming_pcm_chunks",
        "realtime_gate_passed": not fail_reasons,
        "gate_fail_reasons": fail_reasons,
        "gate_thresholds": {
            "max_first_partial_ms": max_first_partial_ms,
            "max_final_latency_ms": max_final_latency_ms,
            "min_partial_events": min_partial_events,
            "min_final_coverage_ratio": min_final_coverage_ratio,
            "max_rtf": max_rtf,
            "fail_on_suspect_final": fail_on_suspect_final,
        },
        "chunk_ms": chunk_ms,
        "input_realtime_pacing": realtime,
        "input_finished_offset_ms": input_finished_offset_ms,
        "partial_before_stop_count": len(partials_before_stop),
        "final_after_stop_count": len(finals_after_stop),
        "first_partial_audio_lag_ms": first_partial_ms if isinstance(first_partial_ms, (int, float)) else None,
        "partial_cadence_ms": summarize_partial_cadence(partial_events),
        "partial_coverage_ratio": partial_coverage_ratio,
        "final_coverage_ratio": final_coverage_ratio,
        "stable_final_after_stop": stable_final_after_stop,
        "partial_after_final": partial_after_final,
        "gate_notes_zh": [
            "本 gate 只认可录音未结束前到达的 partial，完整音频 generate(...) 不算实时 partial。",
            "FunASR 的中途 offline/final segment 只记录为事件，不代表用户会话结束；用户停止输入后才进入最终输出判断。",
        ],
    }


async def run_funasr_ws_gate_case(
    *,
    case: EvalCase,
    ws_url: str,
    out_dir: Path,
    chunk_ms: int,
    realtime: bool,
    receive_timeout_sec: float,
    hotwords: str,
    use_itn: bool,
    mode: str,
    model_info: dict[str, Any],
    max_first_partial_ms: float,
    max_final_latency_ms: float,
    min_partial_events: int,
    min_final_coverage_ratio: float,
    max_rtf: float,
    fail_on_suspect_final: bool,
) -> dict[str, Any]:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python package 'websockets'. Activate the FunASR venv or install FunASR websocket requirements."
        ) from exc

    audio = read_wav_16k_mono_int16(case.audio_path)
    parsed = urlparse(ws_url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError(f"ws-url must start with ws:// or wss://, got {ws_url}")

    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    chunks_path = case_out / "chunks.jsonl"
    summary_path = case_out / "summary.json"
    for path in (events_path, chunks_path):
        if path.exists():
            path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    bytes_per_ms = audio.sample_rate * audio.sample_width * audio.channels / 1000.0
    stride = max(2, int(bytes_per_ms * chunk_ms))
    if stride % 2:
        stride += 1

    events: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    start_perf = time.perf_counter()
    send_started_at = start_perf
    send_finished_at = start_perf
    sender_done = asyncio.Event()

    async with websockets.connect(ws_url, subprotocols=["binary"], ping_interval=None) as websocket:
        start_message = {
            "mode": mode,
            "chunk_size": DEFAULT_FUNASR_CHUNK_SIZE,
            "chunk_interval": DEFAULT_FUNASR_CHUNK_INTERVAL,
            "encoder_chunk_look_back": 4,
            "decoder_chunk_look_back": 0,
            "audio_fs": audio.sample_rate,
            "wav_name": case.case_id,
            "wav_format": "pcm",
            "is_speaking": True,
            "hotwords": hotwords,
            "itn": use_itn,
        }
        await websocket.send(json.dumps(start_message, ensure_ascii=False))

        async def sender() -> None:
            nonlocal send_started_at, send_finished_at
            try:
                send_started_at = time.perf_counter()
                for index, offset in enumerate(range(0, len(audio.pcm), stride)):
                    chunk = audio.pcm[offset : offset + stride]
                    send_offset_ms = monotonic_ms(send_started_at)
                    audio_start_ms = offset / bytes_per_ms
                    audio_end_ms = (offset + len(chunk)) / bytes_per_ms
                    chunk_record = {
                        "case_id": case.case_id,
                        "chunk_index": index,
                        "send_offset_ms": send_offset_ms,
                        "audio_start_ms": audio_start_ms,
                        "audio_end_ms": audio_end_ms,
                        "byte_count": len(chunk),
                    }
                    chunks.append(chunk_record)
                    append_jsonl(chunks_path, chunk_record)
                    await websocket.send(chunk)
                    if realtime:
                        await asyncio.sleep(chunk_ms / 1000.0)
                send_finished_at = time.perf_counter()
                await websocket.send(json.dumps({"is_speaking": False}, ensure_ascii=False))
            finally:
                sender_done.set()

        async def receiver() -> None:
            while True:
                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=receive_timeout_sec)
                except asyncio.TimeoutError:
                    if sender_done.is_set():
                        break
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
                recv_offset = monotonic_ms(send_started_at)
                try:
                    payload = json.loads(raw_message)
                except json.JSONDecodeError:
                    payload = {"raw": raw_message}
                text = str(payload.get("text", ""))
                event_mode = str(payload.get("mode", ""))
                kind = classify_funasr_event(event_mode)
                event = {
                    "recv_epoch_ms": now_ms(),
                    "recv_offset_ms": recv_offset,
                    "case_id": case.case_id,
                    "kind": kind,
                    "mode": event_mode,
                    "text": text,
                    "is_final": bool(payload.get("is_final", False)),
                    "raw": payload,
                }
                events.append(event)
                append_jsonl(events_path, event)

        await asyncio.gather(sender(), receiver())

    wall_clock_finished_at = time.perf_counter()
    input_finished_offset_ms = (send_finished_at - send_started_at) * 1000.0
    event_offsets = [float(e["recv_offset_ms"]) for e in events if isinstance(e.get("recv_offset_ms"), (int, float))]
    effective_finished_offset_ms = max(event_offsets) if event_offsets else input_finished_offset_ms
    effective_finished_at = send_started_at + (effective_finished_offset_ms / 1000.0)
    transcript = select_funasr_transcript(events=events, expected_text=case.expected_text)
    summary = build_result_summary(
        case=case,
        adapter="funasr-ws",
        final_text=str(transcript["final_text"]),
        events=events,
        send_started_at=send_started_at,
        send_finished_at=send_finished_at,
        run_finished_at=effective_finished_at,
        audio=audio,
        status="ok" if transcript["final_text"] else "no_text",
        model_info=model_info,
    )
    summary.update(transcript)
    summary.update(
        evaluate_realtime_gate(
            summary=summary,
            events=events,
            expected_text=case.expected_text,
            input_finished_offset_ms=input_finished_offset_ms,
            chunk_ms=chunk_ms,
            realtime=realtime,
            max_first_partial_ms=max_first_partial_ms,
            max_final_latency_ms=max_final_latency_ms,
            min_partial_events=min_partial_events,
            min_final_coverage_ratio=min_final_coverage_ratio,
            max_rtf=max_rtf,
            fail_on_suspect_final=fail_on_suspect_final,
        )
    )
    summary.update(
        {
            "metric_explanations_zh": GATE_METRIC_EXPLANATIONS_ZH,
            "input_chunk_count": len(chunks),
            "input_chunk_trace": str(chunks_path),
            "effective_finished_offset_ms": effective_finished_offset_ms,
            "wall_clock_run_seconds": wall_clock_finished_at - send_started_at,
        }
    )
    write_json(summary_path, summary)
    return summary


def aggregate_gate_results(
    *,
    summaries: list[dict[str, Any]],
    model_info: dict[str, Any],
    adapter: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    passed = [s for s in summaries if bool(s.get("realtime_gate_passed"))]
    failed = [s for s in summaries if not bool(s.get("realtime_gate_passed"))]
    fail_reason_counts: dict[str, int] = {}
    for summary in failed:
        for reason in summary.get("gate_fail_reasons") or []:
            fail_reason_counts[str(reason)] = fail_reason_counts.get(str(reason), 0) + 1

    aggregate_metrics = {
        "case_count": len(summaries),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "mean_cer": mean_number([s.get("cer") for s in summaries]),
        "mean_wer": mean_number([s.get("wer") for s in summaries]),
        "mean_rtf": mean_number([s.get("rtf") for s in summaries]),
        "mean_first_partial_ms": mean_number([s.get("first_partial_ms") for s in summaries]),
        "mean_final_latency_ms": mean_number([s.get("final_latency_ms") for s in summaries]),
        "mean_partial_event_count": mean_number([s.get("partial_event_count") for s in summaries]),
        "mean_partial_before_stop_count": mean_number([s.get("partial_before_stop_count") for s in summaries]),
        "mean_final_after_stop_count": mean_number([s.get("final_after_stop_count") for s in summaries]),
        "mean_partial_cadence_ms": mean_number([s.get("partial_cadence_ms") for s in summaries]),
        "mean_final_coverage_ratio": mean_number([s.get("final_coverage_ratio") for s in summaries]),
        "fail_reason_counts": fail_reason_counts,
    }
    return {
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "adapter": adapter,
        "model_info": model_info,
        "metric_explanations_zh": GATE_METRIC_EXPLANATIONS_ZH,
        "realtime_gate_passed": len(failed) == 0 and bool(summaries),
        "aggregate_metrics": aggregate_metrics,
        "gate_config": {
            "chunk_ms": args.chunk_ms,
            "input_realtime_pacing": not args.no_realtime,
            "receive_timeout_sec": args.receive_timeout_sec,
            "max_first_partial_ms": args.max_first_partial_ms,
            "max_final_latency_ms": args.max_final_latency_ms,
            "min_partial_events": args.min_partial_events,
            "min_final_coverage_ratio": args.min_final_coverage_ratio,
            "max_rtf": args.max_rtf,
            "fail_on_suspect_final": args.fail_on_suspect_final,
            "warn_only": args.warn_only,
        },
        "cases": summaries,
        "created_epoch_ms": now_ms(),
    }


async def run_cases_async(args: argparse.Namespace) -> int:
    cases = load_cases(Path(args.cases), allow_missing_audio=False)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)
    summaries: list[dict[str, Any]] = []

    for case in cases:
        print(f"realtime-gate {case.case_id} via {args.adapter}")
        try:
            if args.adapter != "funasr-ws":
                raise ValueError(f"unsupported realtime gate adapter: {args.adapter}")
            summary = await run_funasr_ws_gate_case(
                case=case,
                ws_url=args.ws_url,
                out_dir=out_dir,
                chunk_ms=args.chunk_ms,
                realtime=not args.no_realtime,
                receive_timeout_sec=args.receive_timeout_sec,
                hotwords=args.hotwords,
                use_itn=not args.no_itn,
                mode=args.mode,
                model_info=model_info,
                max_first_partial_ms=args.max_first_partial_ms,
                max_final_latency_ms=args.max_final_latency_ms,
                min_partial_events=args.min_partial_events,
                min_final_coverage_ratio=args.min_final_coverage_ratio,
                max_rtf=args.max_rtf,
                fail_on_suspect_final=args.fail_on_suspect_final,
            )
        except Exception as exc:
            summary = {
                "case_id": case.case_id,
                "adapter": args.adapter,
                "model_info": model_info,
                "metric_explanations_zh": GATE_METRIC_EXPLANATIONS_ZH,
                "audio": str(case.audio_path),
                "expected_text": case.expected_text,
                "final_text": "",
                "status": "error",
                "error": str(exc),
                "realtime_gate_passed": False,
                "gate_fail_reasons": ["case_runtime_error"],
            }
            write_json(out_dir / case.case_id / "summary.json", summary)
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    aggregate = aggregate_gate_results(summaries=summaries, model_info=model_info, adapter=args.adapter, args=args)
    write_json(out_dir / "summary.json", aggregate)
    if args.warn_only:
        return 0
    return 0 if bool(aggregate["realtime_gate_passed"]) else 1


def command_run(args: argparse.Namespace) -> int:
    return asyncio.run(run_cases_async(args))


def command_self_test(args: argparse.Namespace) -> int:
    expected = "今天我们测试一段实时语音输入"
    case = EvalCase(
        case_id="unit_gate",
        audio_path=Path("unit.wav"),
        expected_text=expected,
        lang="zh",
        scenario="unit",
        metadata={},
    )
    audio = WavAudio(
        path=Path("unit.wav"),
        sample_rate=16000,
        channels=1,
        sample_width=2,
        frame_count=16000,
        pcm=b"\0" * 32000,
    )
    events = [
        {"kind": "partial", "text": "今天我们测试", "recv_offset_ms": 200.0},
        {"kind": "partial", "text": expected, "recv_offset_ms": 600.0},
        {"kind": "final", "text": expected, "recv_offset_ms": 1200.0},
    ]
    transcript = select_funasr_transcript(events=events, expected_text=expected)
    summary = build_result_summary(
        case=case,
        adapter="funasr-ws",
        final_text=str(transcript["final_text"]),
        events=events,
        send_started_at=0.0,
        send_finished_at=1.0,
        run_finished_at=1.2,
        audio=audio,
        status="ok",
        model_info={},
    )
    summary.update(transcript)
    gate = evaluate_realtime_gate(
        summary=summary,
        events=events,
        expected_text=expected,
        input_finished_offset_ms=1000.0,
        chunk_ms=100,
        realtime=True,
        max_first_partial_ms=1000.0,
        max_final_latency_ms=500.0,
        min_partial_events=1,
        min_final_coverage_ratio=0.70,
        max_rtf=2.0,
        fail_on_suspect_final=False,
    )
    if not gate["realtime_gate_passed"]:
        raise AssertionError(f"expected passing realtime gate, got {gate}")

    late_events = [
        {"kind": "partial", "text": "今天我们测试", "recv_offset_ms": 200.0},
        {"kind": "final", "text": expected, "recv_offset_ms": 900.0},
        {"kind": "partial", "text": "迟到 partial", "recv_offset_ms": 1100.0},
    ]
    transcript = select_funasr_transcript(events=late_events, expected_text=expected)
    summary = build_result_summary(
        case=case,
        adapter="funasr-ws",
        final_text=str(transcript["final_text"]),
        events=late_events,
        send_started_at=0.0,
        send_finished_at=1.0,
        run_finished_at=1.1,
        audio=audio,
        status="ok",
        model_info={},
    )
    summary.update(transcript)
    gate = evaluate_realtime_gate(
        summary=summary,
        events=late_events,
        expected_text=expected,
        input_finished_offset_ms=1000.0,
        chunk_ms=100,
        realtime=True,
        max_first_partial_ms=1000.0,
        max_final_latency_ms=500.0,
        min_partial_events=1,
        min_final_coverage_ratio=0.70,
        max_rtf=2.0,
        fail_on_suspect_final=False,
    )
    if gate["realtime_gate_passed"] or "partial_after_final" not in gate["gate_fail_reasons"]:
        raise AssertionError(f"expected late partial failure, got {gate}")

    file_level_events = [{"kind": "final", "text": expected, "recv_offset_ms": 300.0}]
    transcript = select_funasr_transcript(events=file_level_events, expected_text=expected)
    summary = build_result_summary(
        case=case,
        adapter="file-level",
        final_text=str(transcript["final_text"]),
        events=file_level_events,
        send_started_at=0.0,
        send_finished_at=1.0,
        run_finished_at=1.1,
        audio=audio,
        status="ok",
        model_info={},
    )
    summary.update(transcript)
    gate = evaluate_realtime_gate(
        summary=summary,
        events=file_level_events,
        expected_text=expected,
        input_finished_offset_ms=1000.0,
        chunk_ms=100,
        realtime=True,
        max_first_partial_ms=1000.0,
        max_final_latency_ms=500.0,
        min_partial_events=1,
        min_final_coverage_ratio=0.70,
        max_rtf=2.0,
        fail_on_suspect_final=False,
    )
    expected_reasons = {"no_or_too_few_partial_events", "no_partial_before_user_stop"}
    if gate["realtime_gate_passed"] or not expected_reasons.issubset(set(gate["gate_fail_reasons"])):
        raise AssertionError(f"expected file-level rejection, got {gate}")

    print("ASR realtime gate self-test passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    self_test = sub.add_parser("self-test", help="Run internal realtime gate checks.")
    self_test.set_defaults(func=command_self_test)

    run = sub.add_parser("run", help="Run realtime streaming gate cases.")
    run.add_argument("--adapter", required=True, choices=["funasr-ws"])
    run.add_argument("--cases", required=True)
    run.add_argument("--out-dir", default="eval/asr_streaming/results/realtime-gate")
    run.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    run.add_argument("--model-id", default="paraformer-current-funasr-ws")
    run.add_argument("--ws-url", default="ws://127.0.0.1:10095")
    run.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    run.add_argument("--no-realtime", action="store_true", help="Send chunks without realtime sleeps; diagnostic only.")
    run.add_argument("--receive-timeout-sec", type=float, default=3.0)
    run.add_argument("--hotwords", default="")
    run.add_argument("--no-itn", action="store_true")
    run.add_argument("--mode", default="2pass", choices=["online", "offline", "2pass"])
    run.add_argument("--max-first-partial-ms", type=float, default=1500.0)
    run.add_argument("--max-final-latency-ms", type=float, default=2500.0)
    run.add_argument("--min-partial-events", type=int, default=1)
    run.add_argument("--min-final-coverage-ratio", type=float, default=DEFAULT_MIN_COMPLETE_TEXT_RATIO)
    run.add_argument("--max-rtf", type=float, default=1.50)
    run.add_argument("--fail-on-suspect-final", action="store_true")
    run.add_argument("--warn-only", action="store_true", help="Write summaries but return zero even when the gate fails.")
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
