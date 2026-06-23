#!/usr/bin/env python3
"""Prototype a local Qwen3-ASR MLX cumulative-recompute service contract.

The goal is service behavior, not Swift app integration. The prototype accepts
timed PCM chunks, emits service events, rejects stale session results, and
generates a final result after simulated user stop.

It still uses cumulative recompute over accumulated audio prefixes, so it is not
native realtime streaming and must not be treated as a direct app backend until
the service gate passes.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwen3_mlx_cumulative_probe import (  # noqa: E402
    call_final_generate,
    call_stream_or_generate,
    has_meaningful_text,
)
from qwen3_mlx_realtime_probe import (  # noqa: E402
    classify_model_surface,
    load_mlx_model,
)
from run_eval import (  # noqa: E402
    METRIC_EXPLANATIONS_ZH,
    append_jsonl,
    cer,
    char_length_ratio,
    load_cases,
    load_model_metadata,
    now_ms,
    partial_rewrite_rate,
    read_wav_16k_mono_int16,
    wer,
    write_json,
)


SERVICE_SCHEMA_VERSION = "1.0"
SAMPLE_RATE = 16000

SERVICE_EXPLANATIONS_ZH = {
    **METRIC_EXPLANATIONS_ZH,
    "service_gate_passed": "是否通过累计重算 wrapper 的服务级门槛。它验证 session、partial、finish、final、cancel、stale event 隔离和延迟阈值，但不等于原生 realtime streaming。",
    "native_realtime_gate_eligible": "是否为原生实时流式模型。累计重算 wrapper 固定为 false，因为它没有模型原生 feed/step/close 会话。",
    "service_event": "服务层事件，包括 start、chunk、partial、finish、final、cancel 和 ignored_stale_*。",
    "session_token": "每次 start 生成的会话所有权 token。旧 job 返回时 token 不匹配会被忽略。",
    "revision": "服务层 partial/final 修订号。用于让前端或 App 识别事件顺序。",
    "first_usable_partial_ms": "从模拟录音开始到第一个包含实际文字的 partial 到达的时间，单位毫秒。",
    "partial_before_stop_count": "模拟用户停止录音前已经发出的 partial 数量。浮窗实时体验要求该值大于 0。",
    "final_after_stop_count": "模拟用户停止录音后发出的 final 数量。最终输出必须发生在用户停止之后。",
    "ignored_stale_event_count": "被服务拒绝的旧 session、cancel 后或 final 后 job 数量。非 0 不一定失败；关键是它们没有污染 partial/final。",
    "partial_after_final": "是否存在 final 之后仍被接受的 partial。true 表示服务事件隔离失败。",
    "wrapper_service_candidate": "是否值得进入下一步独立服务工程化。true 仍不代表可以直接接入 Swift App。",
}


@dataclass
class ServiceResult:
    text: str
    wall_ms: float
    mode: str


class MLXBackend:
    def __init__(self, model: Any, *, language: str | None, max_tokens: int):
        self.model = model
        self.language = language
        self.max_tokens = max_tokens

    def partial(self, audio: np.ndarray) -> ServiceResult:
        result = call_stream_or_generate(
            model=self.model,
            audio=audio,
            language=self.language,
            max_tokens=self.max_tokens,
        )
        return ServiceResult(
            text=str(result["text"]).strip(),
            wall_ms=float(result["wall_ms"]),
            mode=str(result["mode"]),
        )

    def final(self, audio: np.ndarray) -> ServiceResult:
        result = call_final_generate(
            model=self.model,
            audio=audio,
            language=self.language,
            max_tokens=self.max_tokens,
        )
        return ServiceResult(
            text=str(result["text"]).strip(),
            wall_ms=float(result["wall_ms"]),
            mode=str(result["mode"]),
        )


class FakeBackend:
    def __init__(self, *, partial_wall_ms: float = 25.0, final_wall_ms: float = 40.0):
        self.partial_wall_ms = partial_wall_ms
        self.final_wall_ms = final_wall_ms

    def partial(self, audio: np.ndarray) -> ServiceResult:
        seconds = len(audio) / float(SAMPLE_RATE)
        text = "你好" if seconds >= 1.0 else ""
        return ServiceResult(text=text, wall_ms=self.partial_wall_ms, mode="fake_partial")

    def final(self, audio: np.ndarray) -> ServiceResult:
        return ServiceResult(text="你好世界", wall_ms=self.final_wall_ms, mode="fake_final")


@dataclass
class SessionState:
    session_id: str
    token: int
    status: str = "recording"
    chunks: list[np.ndarray] = field(default_factory=list)
    revision: int = 0
    next_prefix_seconds: float = 1.0
    emitted_prefix_count: int = 0
    input_finished_offset_ms: float | None = None
    final_text: str = ""

    @property
    def audio(self) -> np.ndarray:
        if not self.chunks:
            return np.zeros((0,), dtype=np.float32)
        return np.concatenate(self.chunks)

    @property
    def duration_seconds(self) -> float:
        return len(self.audio) / float(SAMPLE_RATE)


class CumulativeRecomputeService:
    def __init__(
        self,
        *,
        backend: Any,
        prefix_step_sec: float,
        min_prefix_sec: float,
        max_prefixes: int,
    ):
        self.backend = backend
        self.prefix_step_sec = max(0.1, prefix_step_sec)
        self.min_prefix_sec = max(0.1, min_prefix_sec)
        self.max_prefixes = max(1, max_prefixes)
        self.sessions: dict[str, SessionState] = {}
        self.events: list[dict[str, Any]] = []
        self.worker_available_ms = 0.0
        self._token_counter = 0

    def start(self, session_id: str, *, simulated_now_ms: float = 0.0, session_token: int | None = None) -> int:
        if session_token is None:
            self._token_counter += 1
            token = self._token_counter
        else:
            token = int(session_token)
            self._token_counter = max(self._token_counter, token)
        self.worker_available_ms = simulated_now_ms
        self.sessions[session_id] = SessionState(
            session_id=session_id,
            token=token,
            next_prefix_seconds=self.min_prefix_sec,
        )
        self._append_event(
            {
                "kind": "session_started",
                "session_id": session_id,
                "session_token": token,
                "recv_offset_ms": simulated_now_ms,
                "is_final": False,
            }
        )
        return token

    def push_pcm(
        self,
        session_id: str,
        pcm_float32: np.ndarray,
        *,
        simulated_now_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
    ) -> None:
        session = self.sessions.get(session_id)
        if session is None or session.status != "recording":
            self._append_event(
                {
                    "kind": "ignored_chunk",
                    "session_id": session_id,
                    "recv_offset_ms": simulated_now_ms,
                    "reason": "session_not_recording",
                    "chunk_index": chunk_index,
                    "audio_start_ms": audio_start_ms,
                    "audio_end_ms": audio_end_ms,
                    "is_final": False,
                }
            )
            return

        session.chunks.append(pcm_float32)
        self._append_event(
            {
                "kind": "chunk_received",
                "session_id": session_id,
                "session_token": session.token,
                "recv_offset_ms": simulated_now_ms,
                "chunk_index": chunk_index,
                "audio_start_ms": audio_start_ms,
                "audio_end_ms": audio_end_ms,
                "sample_count": int(len(pcm_float32)),
                "is_final": False,
            }
        )
        self._maybe_emit_prefixes(session, simulated_now_ms=simulated_now_ms)

    def finish(self, session_id: str, *, simulated_now_ms: float) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if session is None:
            return self._append_event(
                {
                    "kind": "ignored_finish",
                    "session_id": session_id,
                    "recv_offset_ms": simulated_now_ms,
                    "reason": "missing_session",
                    "is_final": False,
                }
            )
        if session.status == "canceled":
            return self._append_event(
                {
                    "kind": "ignored_finish",
                    "session_id": session_id,
                    "session_token": session.token,
                    "recv_offset_ms": simulated_now_ms,
                    "reason": "session_canceled",
                    "is_final": False,
                }
            )
        if session.status == "finalized":
            return self._append_event(
                {
                    "kind": "ignored_finish",
                    "session_id": session_id,
                    "session_token": session.token,
                    "recv_offset_ms": simulated_now_ms,
                    "reason": "session_already_finalized",
                    "is_final": False,
                }
            )

        session.input_finished_offset_ms = simulated_now_ms
        session.status = "finishing"
        self._append_event(
            {
                "kind": "finish_requested",
                "session_id": session_id,
                "session_token": session.token,
                "recv_offset_ms": simulated_now_ms,
                "audio_duration_seconds": session.duration_seconds,
                "is_final": False,
            }
        )

        start_ms = max(simulated_now_ms, self.worker_available_ms)
        result = self.backend.final(session.audio)
        emit_ms = start_ms + result.wall_ms
        self.worker_available_ms = emit_ms
        session.status = "finalized"
        session.revision += 1
        session.final_text = result.text
        return self._append_event(
            {
                "kind": "final",
                "session_id": session_id,
                "session_token": session.token,
                "revision": session.revision,
                "recv_offset_ms": emit_ms,
                "ready_offset_ms": simulated_now_ms,
                "compute_wall_ms": result.wall_ms,
                "mode": result.mode,
                "text": result.text,
                "is_final": True,
            }
        )

    def cancel(self, session_id: str, *, simulated_now_ms: float) -> None:
        session = self.sessions.get(session_id)
        if session is not None:
            session.status = "canceled"
            token = session.token
        else:
            token = None
        self._append_event(
            {
                "kind": "session_canceled",
                "session_id": session_id,
                "session_token": token,
                "recv_offset_ms": simulated_now_ms,
                "is_final": False,
            }
        )

    def deliver_partial_result(
        self,
        *,
        session_id: str,
        session_token: int,
        revision: int,
        text: str,
        ready_offset_ms: float,
        compute_wall_ms: float,
        audio_end_ms: float,
        mode: str = "manual",
    ) -> bool:
        session = self.sessions.get(session_id)
        emit_ms = max(ready_offset_ms, self.worker_available_ms) + compute_wall_ms
        self.worker_available_ms = max(self.worker_available_ms, emit_ms)
        if session is None:
            self._ignored_stale_partial(
                session_id=session_id,
                session_token=session_token,
                revision=revision,
                recv_offset_ms=emit_ms,
                reason="missing_session",
                text=text,
            )
            return False
        if session.token != session_token:
            self._ignored_stale_partial(
                session_id=session_id,
                session_token=session_token,
                revision=revision,
                recv_offset_ms=emit_ms,
                reason="session_token_mismatch",
                text=text,
                current_session_token=session.token,
            )
            return False
        if session.status != "recording":
            self._ignored_stale_partial(
                session_id=session_id,
                session_token=session_token,
                revision=revision,
                recv_offset_ms=emit_ms,
                reason=f"session_not_recording:{session.status}",
                text=text,
            )
            return False
        self._append_event(
            {
                "kind": "partial",
                "session_id": session_id,
                "session_token": session_token,
                "revision": revision,
                "recv_offset_ms": emit_ms,
                "ready_offset_ms": ready_offset_ms,
                "compute_wall_ms": compute_wall_ms,
                "audio_end_ms": audio_end_ms,
                "mode": mode,
                "text": text,
                "meaningful_text": has_meaningful_text(text),
                "is_final": False,
            }
        )
        return True

    def _maybe_emit_prefixes(self, session: SessionState, *, simulated_now_ms: float) -> None:
        while (
            session.status == "recording"
            and session.emitted_prefix_count < self.max_prefixes
            and session.duration_seconds + 1e-9 >= session.next_prefix_seconds
        ):
            prefix_seconds = session.next_prefix_seconds
            sample_count = min(len(session.audio), int(prefix_seconds * SAMPLE_RATE))
            prefix_audio = session.audio[:sample_count]
            ready_ms = prefix_seconds * 1000.0
            start_ms = max(ready_ms, self.worker_available_ms)
            result = self.backend.partial(prefix_audio)
            session.revision += 1
            accepted = self.deliver_partial_result(
                session_id=session.session_id,
                session_token=session.token,
                revision=session.revision,
                text=result.text,
                ready_offset_ms=start_ms,
                compute_wall_ms=result.wall_ms,
                audio_end_ms=prefix_seconds * 1000.0,
                mode=result.mode,
            )
            if accepted:
                session.emitted_prefix_count += 1
            session.next_prefix_seconds += self.prefix_step_sec

    def _ignored_stale_partial(self, **event: Any) -> dict[str, Any]:
        event.setdefault("kind", "ignored_stale_partial")
        event.setdefault("is_final", False)
        return self._append_event(event)

    def _append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event.setdefault("recv_epoch_ms", now_ms())
        self.events.append(event)
        return event


def mean_number(values: list[Any]) -> float | None:
    numbers = [float(v) for v in values if isinstance(v, (int, float))]
    return statistics.mean(numbers) if numbers else None


def partial_cadence_ms(partials: list[dict[str, Any]]) -> float | None:
    offsets = [float(p["recv_offset_ms"]) for p in partials if isinstance(p.get("recv_offset_ms"), (int, float))]
    if len(offsets) < 2:
        return None
    return statistics.mean([b - a for a, b in zip(offsets, offsets[1:])])


def evaluate_service_gate(
    *,
    events: list[dict[str, Any]],
    expected_text: str,
    input_finished_offset_ms: float,
    max_first_usable_partial_ms: float,
    max_final_latency_ms: float,
    max_final_cer: float,
) -> dict[str, Any]:
    partials = [e for e in events if e.get("kind") == "partial" and e.get("text")]
    meaningful_partials = [e for e in partials if bool(e.get("meaningful_text"))]
    finals = [e for e in events if e.get("kind") == "final" and e.get("text")]
    ignored = [e for e in events if str(e.get("kind", "")).startswith("ignored")]
    partials_before_stop = [
        e
        for e in partials
        if isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) <= input_finished_offset_ms
    ]
    finals_after_stop = [
        e
        for e in finals
        if isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) >= input_finished_offset_ms
    ]
    final_text = str(finals[-1]["text"]) if finals else ""
    final_offset = float(finals[-1]["recv_offset_ms"]) if finals else None
    final_latency = None if final_offset is None else final_offset - input_finished_offset_ms
    first_usable = (
        float(meaningful_partials[0]["recv_offset_ms"])
        if meaningful_partials and isinstance(meaningful_partials[0].get("recv_offset_ms"), (int, float))
        else None
    )
    partial_after_final = bool(
        final_offset is not None
        and any(float(p.get("recv_offset_ms", 0.0)) > final_offset for p in partials)
    )
    final_cer = cer(expected_text, final_text)
    fail_reasons: list[str] = []

    if not partials_before_stop:
        fail_reasons.append("no_partial_before_user_stop")
    if first_usable is None:
        fail_reasons.append("missing_first_usable_partial")
    elif first_usable > max_first_usable_partial_ms:
        fail_reasons.append("first_usable_partial_too_slow")
    if not final_text:
        fail_reasons.append("missing_final_text")
    if not finals_after_stop:
        fail_reasons.append("no_final_after_user_stop")
    if final_latency is None:
        fail_reasons.append("missing_final_latency")
    elif final_latency > max_final_latency_ms:
        fail_reasons.append("final_latency_too_slow")
    if final_cer is None:
        fail_reasons.append("missing_final_cer")
    elif final_cer > max_final_cer:
        fail_reasons.append("final_cer_too_high")
    if partial_after_final:
        fail_reasons.append("partial_after_final")

    return {
        "service_gate_passed": not fail_reasons,
        "service_gate_fail_reasons": fail_reasons,
        "native_realtime_gate_eligible": False,
        "wrapper_service_candidate": not fail_reasons,
        "thresholds": {
            "max_first_usable_partial_ms": max_first_usable_partial_ms,
            "max_final_latency_ms": max_final_latency_ms,
            "max_final_cer": max_final_cer,
        },
        "partial_before_stop_count": len(partials_before_stop),
        "final_after_stop_count": len(finals_after_stop),
        "first_usable_partial_ms": first_usable,
        "final_latency_ms": final_latency,
        "partial_cadence_ms": partial_cadence_ms(partials),
        "ignored_stale_event_count": len(ignored),
        "partial_after_final": partial_after_final,
        "final_text": final_text,
        "final_cer": final_cer,
        "final_wer": wer(expected_text, final_text),
        "final_to_expected_char_ratio": char_length_ratio(final_text, expected_text),
        "reason_not_native_realtime": (
            "This service uses cumulative recompute on accumulated prefix audio. "
            "It validates wrapper service behavior, not native model feed/step/close semantics."
        ),
    }


def wav_pcm_float32(audio_path: Path) -> tuple[np.ndarray, float]:
    wav = read_wav_16k_mono_int16(audio_path)
    pcm = np.frombuffer(wav.pcm, dtype="<i2").astype(np.float32) / 32768.0
    return pcm, wav.duration_seconds


def run_service_case(
    *,
    case: Any,
    service: CumulativeRecomputeService,
    out_dir: Path,
    chunk_ms: int,
    max_first_usable_partial_ms: float,
    max_final_latency_ms: float,
    max_final_cer: float,
    model_info: dict[str, Any],
) -> dict[str, Any]:
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    chunks_path = case_out / "chunks.jsonl"
    for path in (events_path, chunks_path):
        if path.exists():
            path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    pcm, duration_seconds = wav_pcm_float32(case.audio_path)
    stride = max(1, int(SAMPLE_RATE * chunk_ms / 1000.0))
    session_id = case.case_id
    service.start(session_id, simulated_now_ms=0.0)
    chunk_records: list[dict[str, Any]] = []
    for index, offset in enumerate(range(0, len(pcm), stride)):
        chunk = pcm[offset : offset + stride]
        audio_start_ms = offset / SAMPLE_RATE * 1000.0
        audio_end_ms = (offset + len(chunk)) / SAMPLE_RATE * 1000.0
        chunk_record = {
            "case_id": case.case_id,
            "chunk_index": index,
            "audio_start_ms": audio_start_ms,
            "audio_end_ms": audio_end_ms,
            "sample_count": int(len(chunk)),
        }
        chunk_records.append(chunk_record)
        append_jsonl(chunks_path, chunk_record)
        service.push_pcm(
            session_id,
            chunk,
            simulated_now_ms=audio_end_ms,
            audio_start_ms=audio_start_ms,
            audio_end_ms=audio_end_ms,
            chunk_index=index,
        )
    input_finished_offset_ms = duration_seconds * 1000.0
    service.finish(session_id, simulated_now_ms=input_finished_offset_ms)

    case_events = [e for e in service.events if e.get("session_id") == session_id]
    for event in case_events:
        append_jsonl(events_path, event)
    gate = evaluate_service_gate(
        events=case_events,
        expected_text=case.expected_text,
        input_finished_offset_ms=input_finished_offset_ms,
        max_first_usable_partial_ms=max_first_usable_partial_ms,
        max_final_latency_ms=max_final_latency_ms,
        max_final_cer=max_final_cer,
    )
    partial_texts = [str(e.get("text", "")) for e in case_events if e.get("kind") == "partial" and e.get("text")]
    summary = {
        "schema_version": SERVICE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "case_id": case.case_id,
        "model_info": model_info,
        "metric_explanations_zh": SERVICE_EXPLANATIONS_ZH,
        "audio": str(case.audio_path),
        "duration_seconds": duration_seconds,
        "input_finished_offset_ms": input_finished_offset_ms,
        "chunk_ms": chunk_ms,
        "chunk_count": len(chunk_records),
        "lang": case.lang,
        "scenario": case.scenario,
        "expected_text": case.expected_text,
        "service_contract": ["start", "push_pcm", "partial", "finish", "final", "cancel"],
        "gate": gate,
        "final_text": gate["final_text"],
        "cer": gate["final_cer"],
        "wer": gate["final_wer"],
        "partial_event_count": len([e for e in case_events if e.get("kind") == "partial"]),
        "final_event_count": len([e for e in case_events if e.get("kind") == "final"]),
        "event_count": len(case_events),
        "partial_rewrite_rate": partial_rewrite_rate(partial_texts),
        "native_realtime_gate_eligible": False,
        "wrapper_service_candidate": gate["wrapper_service_candidate"],
    }
    write_json(case_out / "summary.json", summary)
    return summary


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


def command_run(args: argparse.Namespace) -> int:
    cases = filter_cases(load_cases(Path(args.cases), allow_missing_audio=False), args.case_id)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)

    load_started = time.perf_counter()
    model = load_mlx_model(args.model, args.mlx_audio_source)
    load_wall_ms = (time.perf_counter() - load_started) * 1000.0
    backend = MLXBackend(
        model,
        language=args.language.strip() or None,
        max_tokens=args.max_tokens,
    )
    service = CumulativeRecomputeService(
        backend=backend,
        prefix_step_sec=args.prefix_step_sec,
        min_prefix_sec=args.min_prefix_sec,
        max_prefixes=args.max_prefixes,
    )
    case_summaries = [
        run_service_case(
            case=case,
            service=service,
            out_dir=out_dir,
            chunk_ms=args.chunk_ms,
            max_first_usable_partial_ms=args.max_first_usable_partial_ms,
            max_final_latency_ms=args.max_final_latency_ms,
            max_final_cer=args.max_final_cer,
            model_info=model_info,
        )
        for case in cases
    ]
    service_passes = [bool(s["gate"]["service_gate_passed"]) for s in case_summaries]
    summary = {
        "schema_version": SERVICE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "model": args.model,
        "model_id": args.model_id,
        "model_info": model_info,
        "metric_explanations_zh": SERVICE_EXPLANATIONS_ZH,
        "api_surface": classify_model_surface(model),
        "model_load_wall_ms": load_wall_ms,
        "case_count": len(case_summaries),
        "case_ids": [s["case_id"] for s in case_summaries],
        "aggregate_status": (
            "all_service_cases_passed_not_native_realtime"
            if all(service_passes)
            else "mixed_or_failed_service_cases"
        ),
        "native_realtime_gate_eligible": False,
        "wrapper_service_candidate": all(service_passes),
        "case_summaries": case_summaries,
        "final_recommendation": {
            "use_as_app_realtime_backend_now": False,
            "reason": (
                "This validates an in-process cumulative-recompute service contract. "
                "A production backend still needs an actual local service boundary, "
                "resource management, and Swift-side integration validation."
            ),
        },
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def command_self_test(args: argparse.Namespace) -> int:
    service = CumulativeRecomputeService(
        backend=FakeBackend(),
        prefix_step_sec=1.0,
        min_prefix_sec=1.0,
        max_prefixes=2,
    )
    old_token = service.start("same", simulated_now_ms=0.0)
    new_token = service.start("same", simulated_now_ms=10.0)
    accepted_old = service.deliver_partial_result(
        session_id="same",
        session_token=old_token,
        revision=1,
        text="old text",
        ready_offset_ms=20.0,
        compute_wall_ms=5.0,
        audio_end_ms=1000.0,
    )
    if accepted_old:
        raise AssertionError("old session partial must be ignored")
    accepted_new = service.deliver_partial_result(
        session_id="same",
        session_token=new_token,
        revision=1,
        text="new text",
        ready_offset_ms=30.0,
        compute_wall_ms=5.0,
        audio_end_ms=1000.0,
    )
    if not accepted_new:
        raise AssertionError("current session partial should be accepted")
    if not any(e.get("kind") == "ignored_stale_partial" for e in service.events):
        raise AssertionError("stale partial ignore event was not recorded")

    finish_service = CumulativeRecomputeService(
        backend=FakeBackend(),
        prefix_step_sec=1.0,
        min_prefix_sec=1.0,
        max_prefixes=2,
    )
    token = finish_service.start("finish", simulated_now_ms=0.0)
    finish_service.finish("finish", simulated_now_ms=1000.0)
    accepted_late = finish_service.deliver_partial_result(
        session_id="finish",
        session_token=token,
        revision=99,
        text="late text",
        ready_offset_ms=900.0,
        compute_wall_ms=200.0,
        audio_end_ms=1000.0,
    )
    if accepted_late:
        raise AssertionError("late partial after final must be ignored")
    final_events = [e for e in finish_service.events if e.get("kind") == "final"]
    partial_events = [e for e in finish_service.events if e.get("kind") == "partial"]
    if len(final_events) != 1 or partial_events:
        raise AssertionError(f"unexpected final/partial events after finish: {finish_service.events}")

    cancel_service = CumulativeRecomputeService(
        backend=FakeBackend(),
        prefix_step_sec=1.0,
        min_prefix_sec=1.0,
        max_prefixes=2,
    )
    cancel_token = cancel_service.start("cancel", simulated_now_ms=0.0)
    cancel_service.cancel("cancel", simulated_now_ms=100.0)
    cancel_service.finish("cancel", simulated_now_ms=200.0)
    accepted_cancel = cancel_service.deliver_partial_result(
        session_id="cancel",
        session_token=cancel_token,
        revision=1,
        text="should not appear",
        ready_offset_ms=200.0,
        compute_wall_ms=5.0,
        audio_end_ms=1000.0,
    )
    if accepted_cancel:
        raise AssertionError("partial after cancel must be ignored")
    if any(e.get("kind") == "final" for e in cancel_service.events):
        raise AssertionError(f"cancel must not produce final: {cancel_service.events}")

    fake_case_events = [
        {"kind": "partial", "recv_offset_ms": 500.0, "text": "你好", "meaningful_text": True},
        {"kind": "final", "recv_offset_ms": 1200.0, "text": "你好世界", "is_final": True},
    ]
    gate = evaluate_service_gate(
        events=fake_case_events,
        expected_text="你好世界",
        input_finished_offset_ms=1000.0,
        max_first_usable_partial_ms=1000.0,
        max_final_latency_ms=500.0,
        max_final_cer=0.1,
    )
    if not gate["service_gate_passed"] or gate["native_realtime_gate_eligible"]:
        raise AssertionError(f"fake passing gate malformed: {gate}")

    multi_session_service = CumulativeRecomputeService(
        backend=FakeBackend(),
        prefix_step_sec=1.0,
        min_prefix_sec=1.0,
        max_prefixes=1,
    )
    multi_session_service.start("first", simulated_now_ms=0.0)
    multi_session_service.finish("first", simulated_now_ms=48000.0)
    multi_session_service.start("second", simulated_now_ms=0.0)
    multi_session_service.push_pcm(
        "second",
        np.zeros((SAMPLE_RATE,), dtype=np.float32),
        simulated_now_ms=1000.0,
        audio_start_ms=0.0,
        audio_end_ms=1000.0,
        chunk_index=0,
    )
    second_partials = [
        e
        for e in multi_session_service.events
        if e.get("session_id") == "second" and e.get("kind") == "partial"
    ]
    if not second_partials or float(second_partials[0]["recv_offset_ms"]) > 2000.0:
        raise AssertionError(f"new sessions must not inherit previous session worker delay: {multi_session_service.events}")

    print("Qwen3 MLX cumulative service self-test passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    self_test = sub.add_parser("self-test", help="Run service-state self-tests without model weights.")
    self_test.set_defaults(func=command_self_test)

    run = sub.add_parser("run", help="Run the cumulative service prototype against local WAV cases.")
    run.add_argument("--model", default=".external/models/mlx-community__Qwen3-ASR-0.6B-8bit")
    run.add_argument("--model-id", default="qwen3-asr-0.6b-mlx-8bit")
    run.add_argument("--mlx-audio-source", default=".external/repos/mlx-audio")
    run.add_argument("--cases", default="eval/asr_streaming/cases.smoke.local.jsonl")
    run.add_argument("--case-id", action="append", default=[], help="Case id to run; can be repeated or comma-separated.")
    run.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    run.add_argument("--language", default="Chinese")
    run.add_argument("--chunk-ms", type=int, default=100)
    run.add_argument("--min-prefix-sec", type=float, default=1.0)
    run.add_argument("--prefix-step-sec", type=float, default=1.0)
    run.add_argument("--max-prefixes", type=int, default=8)
    run.add_argument("--max-tokens", type=int, default=256)
    run.add_argument("--max-first-usable-partial-ms", type=float, default=2500.0)
    run.add_argument("--max-final-latency-ms", type=float, default=2500.0)
    run.add_argument("--max-final-cer", type=float, default=0.15)
    run.add_argument("--out-dir", default="eval/asr_streaming/results/qwen3-mlx-cumulative-service")
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
