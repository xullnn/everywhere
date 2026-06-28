#!/usr/bin/env python3
"""Segmented-cache service prototype for Qwen3-ASR MLX.

This is an evaluation/runtime prototype, not the macOS App integration. It
keeps the same user-visible contract as the existing cumulative service
(`partial` while recording, one `final` after stop) but commits bounded audio
segments internally so long dictation does not require final recognition of the
entire session.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwen3_mlx_cumulative_service import (  # noqa: E402
    MLXBackend,
    SAMPLE_RATE,
    ServiceResult,
    evaluate_service_gate,
)
from qwen3_mlx_realtime_probe import classify_model_surface, load_mlx_model  # noqa: E402
from run_eval import (  # noqa: E402
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
DEFAULT_SPOOL_DIR = Path("eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-spool")

METRIC_EXPLANATIONS_ZH: dict[str, str] = {
    "segment_count": "已提交片段数量。数量越多，单段越短，长语音停止时需要补算的音频越少。",
    "partial_event_count": "录音中用户可见的实时草稿更新次数。",
    "final_latency_ms": "用户停止录音后，到最终文本可用之间的等待时间，单位毫秒。",
    "cache_bytes": "本地缓存音频字节数。用于确认音频已落盘，降低长输入中途丢失风险。",
    "cer": "字符错误率，越低越好；fake 模式不把它作为模型准确率证据。",
    "wer": "词或 token 错误率，越低越好；中文近似按单字 token。",
    "rtf": "实时因子，处理耗时除以音频时长；小于 1 通常表示处理速度快于音频播放速度。",
}


@dataclass(frozen=True)
class SegmentPolicy:
    max_segment_sec: float = 30.0
    min_segment_sec: float = 5.0
    soft_text_chars: int = 150
    partial_step_sec: float = 1.0
    max_partials_per_segment: int = 8

    def validate(self) -> None:
        if self.max_segment_sec <= 0:
            raise ValueError("max_segment_sec must be > 0")
        if self.min_segment_sec <= 0:
            raise ValueError("min_segment_sec must be > 0")
        if self.min_segment_sec > self.max_segment_sec:
            raise ValueError("min_segment_sec must be <= max_segment_sec")
        if self.soft_text_chars < 0:
            raise ValueError("soft_text_chars must be >= 0")
        if self.partial_step_sec <= 0:
            raise ValueError("partial_step_sec must be > 0")
        if self.max_partials_per_segment < 0:
            raise ValueError("max_partials_per_segment must be >= 0")


@dataclass
class SegmentRecord:
    index: int
    audio_start_ms: float
    audio_end_ms: float
    sample_count: int
    cache_path: Path
    final_text: str
    compute_wall_ms: float
    committed_offset_ms: float
    mode: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "audio_start_ms": round3(self.audio_start_ms),
            "audio_end_ms": round3(self.audio_end_ms),
            "duration_ms": round3(self.audio_end_ms - self.audio_start_ms),
            "sample_count": self.sample_count,
            "cache_path": str(self.cache_path),
            "final_text": self.final_text,
            "compute_wall_ms": round3(self.compute_wall_ms),
            "committed_offset_ms": round3(self.committed_offset_ms),
            "mode": self.mode,
        }


@dataclass
class SegmentedSessionState:
    session_id: str
    token: int
    status: str
    cache_dir: Path
    started_offset_ms: float
    active_segment_index: int = 1
    active_segment_start_ms: float = 0.0
    active_chunks: list[np.ndarray] = field(default_factory=list)
    active_next_prefix_sec: float = 1.0
    active_emitted_prefix_count: int = 0
    active_partial_text: str = ""
    revision: int = 0
    committed_segments: list[SegmentRecord] = field(default_factory=list)
    input_finished_offset_ms: float | None = None
    final_text: str = ""

    @property
    def active_audio(self) -> np.ndarray:
        if not self.active_chunks:
            return np.zeros((0,), dtype=np.float32)
        return np.concatenate(self.active_chunks)

    @property
    def active_duration_seconds(self) -> float:
        return len(self.active_audio) / float(SAMPLE_RATE)

    @property
    def committed_text(self) -> str:
        return join_text_parts([segment.final_text for segment in self.committed_segments])

    @property
    def session_audio_path(self) -> Path:
        return self.cache_dir / "session.f32le"

    @property
    def metadata_path(self) -> Path:
        return self.cache_dir / "session.json"

    def segment_cache_path(self, index: int | None = None) -> Path:
        segment_index = self.active_segment_index if index is None else index
        return self.cache_dir / f"segment_{segment_index:03d}.f32le"


class ExpectedTextFakeBackend:
    """Fake backend focused on protocol behavior, not ASR quality."""

    def __init__(self) -> None:
        self.expected_text = "你好世界"
        self.partial_wall_ms = 25.0
        self.final_wall_ms = 50.0

    def set_expected_text(self, text: str) -> None:
        stripped = text.strip()
        if stripped:
            self.expected_text = stripped

    def partial(self, audio: np.ndarray) -> ServiceResult:
        seconds = len(audio) / float(SAMPLE_RATE)
        if seconds < 0.5:
            return ServiceResult(text="", wall_ms=self.partial_wall_ms, mode="fake_partial_waiting")
        split = max(1, len(self.expected_text) // 2)
        return ServiceResult(text=self.expected_text[:split], wall_ms=self.partial_wall_ms, mode="fake_partial")

    def final(self, audio: np.ndarray) -> ServiceResult:
        return ServiceResult(text=self.expected_text, wall_ms=self.final_wall_ms, mode="fake_final")


class SegmentedCacheService:
    def __init__(
        self,
        *,
        backend: Any,
        policy: SegmentPolicy,
        spool_dir: Path = DEFAULT_SPOOL_DIR,
    ) -> None:
        policy.validate()
        self.backend = backend
        self.policy = policy
        self.spool_dir = spool_dir
        self.sessions: dict[str, SegmentedSessionState] = {}
        self.events: list[dict[str, Any]] = []
        self._next_token = 1
        self.worker_available_ms = 0.0

    def start(
        self,
        session_id: str,
        *,
        simulated_now_ms: float = 0.0,
        session_token: int | None = None,
    ) -> int:
        token = session_token if session_token is not None else self._allocate_token()
        cache_dir = self.spool_dir / f"{safe_component(session_id)}-{token}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        session = SegmentedSessionState(
            session_id=session_id,
            token=token,
            status="recording",
            cache_dir=cache_dir,
            started_offset_ms=simulated_now_ms,
            active_next_prefix_sec=self.policy.partial_step_sec,
        )
        self.sessions[session_id] = session
        self.worker_available_ms = min(self.worker_available_ms, simulated_now_ms)
        self._write_session_metadata(session)
        self._append_event(
            {
                "kind": "session_started",
                "session_id": session_id,
                "session_token": token,
                "recv_offset_ms": simulated_now_ms,
                "cache_dir": str(cache_dir),
                "segment_policy": policy_dict(self.policy),
                "is_final": False,
                "accepted": False,
            }
        )
        return token

    def push_pcm(
        self,
        session_id: str,
        audio: np.ndarray,
        *,
        simulated_now_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
        session_token: int | None = None,
    ) -> None:
        session = self._current_recording_session(
            session_id,
            session_token=session_token,
            recv_offset_ms=simulated_now_ms,
            ignored_kind="ignored_stale_chunk",
        )
        if session is None:
            return
        pcm = np.asarray(audio, dtype=np.float32)
        session.active_chunks.append(pcm)
        append_float32(session.session_audio_path, pcm)
        append_float32(session.segment_cache_path(), pcm)
        self._append_event(
            {
                "kind": "chunk_received",
                "session_id": session_id,
                "session_token": session.token,
                "chunk_index": chunk_index,
                "recv_offset_ms": simulated_now_ms,
                "audio_start_ms": audio_start_ms,
                "audio_end_ms": audio_end_ms,
                "sample_count": int(len(pcm)),
                "cache_path": str(session.segment_cache_path()),
                "is_final": False,
                "accepted": False,
            }
        )
        self._maybe_emit_partials(session, simulated_now_ms=simulated_now_ms)
        self._maybe_commit_active_segment(session, simulated_now_ms=simulated_now_ms)
        self._write_session_metadata(session)

    def finish(
        self,
        session_id: str,
        *,
        simulated_now_ms: float,
        session_token: int | None = None,
    ) -> dict[str, Any] | None:
        session = self._current_session(
            session_id,
            session_token=session_token,
            recv_offset_ms=simulated_now_ms,
            ignored_kind="ignored_stale_finish",
        )
        if session is None:
            return None
        if session.status == "canceled":
            self._append_ignored(
                kind="ignored_stale_finish",
                session_id=session_id,
                session_token=session_token,
                current_session_token=session.token,
                recv_offset_ms=simulated_now_ms,
                reason="session_canceled",
            )
            return None
        if session.status == "finalized":
            self._append_ignored(
                kind="ignored_stale_finish",
                session_id=session_id,
                session_token=session.token,
                recv_offset_ms=simulated_now_ms,
                reason="session_already_finalized",
            )
            return None

        session.status = "finishing"
        session.input_finished_offset_ms = simulated_now_ms
        self._append_event(
            {
                "kind": "finish_requested",
                "session_id": session_id,
                "session_token": session.token,
                "recv_offset_ms": simulated_now_ms,
                "active_duration_seconds": round3(session.active_duration_seconds),
                "committed_segment_count": len(session.committed_segments),
                "is_final": False,
                "accepted": False,
            }
        )
        if len(session.active_audio) > 0:
            self._commit_active_segment(session, simulated_now_ms=simulated_now_ms, reason="finish")
        final_recv_ms = max(simulated_now_ms, self.worker_available_ms)
        session.status = "finalized"
        session.revision += 1
        session.final_text = session.committed_text
        event = self._append_event(
            {
                "kind": "final",
                "session_id": session_id,
                "session_token": session.token,
                "revision": session.revision,
                "recv_offset_ms": final_recv_ms,
                "ready_offset_ms": simulated_now_ms,
                "compute_wall_ms": 0.0,
                "mode": "segmented_cache_merge_final",
                "text": session.final_text,
                "segment_count": len(session.committed_segments),
                "merge_strategy": "zero_overlap_concat",
                "cache_dir": str(session.cache_dir),
                "is_final": True,
                "accepted": True,
            }
        )
        self._write_session_metadata(session)
        return event

    def cancel(
        self,
        session_id: str,
        *,
        simulated_now_ms: float,
        session_token: int | None = None,
    ) -> None:
        session = self._current_session(
            session_id,
            session_token=session_token,
            recv_offset_ms=simulated_now_ms,
            ignored_kind="ignored_stale_cancel",
        )
        if session is not None:
            session.status = "canceled"
            self._write_session_metadata(session)
            token = session.token
        else:
            token = session_token
        self._append_event(
            {
                "kind": "session_canceled",
                "session_id": session_id,
                "session_token": token,
                "recv_offset_ms": simulated_now_ms,
                "is_final": False,
                "accepted": False,
            }
        )

    def _maybe_emit_partials(self, session: SegmentedSessionState, *, simulated_now_ms: float) -> None:
        while (
            session.status == "recording"
            and session.active_emitted_prefix_count < self.policy.max_partials_per_segment
            and session.active_duration_seconds + 1e-9 >= session.active_next_prefix_sec
        ):
            prefix_sec = session.active_next_prefix_sec
            sample_count = min(len(session.active_audio), int(prefix_sec * SAMPLE_RATE))
            prefix_audio = session.active_audio[:sample_count]
            ready_ms = session.active_segment_start_ms + prefix_sec * 1000.0
            start_ms = max(ready_ms, self.worker_available_ms)
            result = self.backend.partial(prefix_audio)
            emit_ms = start_ms + result.wall_ms
            self.worker_available_ms = emit_ms
            session.active_partial_text = result.text
            session.revision += 1
            self._emit_visible_partial(
                session,
                text=join_text_parts([session.committed_text, result.text]),
                recv_offset_ms=emit_ms,
                ready_offset_ms=ready_ms,
                compute_wall_ms=result.wall_ms,
                audio_end_ms=ready_ms,
                mode=result.mode,
            )
            session.active_emitted_prefix_count += 1
            session.active_next_prefix_sec += self.policy.partial_step_sec

    def _maybe_commit_active_segment(self, session: SegmentedSessionState, *, simulated_now_ms: float) -> None:
        duration = session.active_duration_seconds
        if duration <= 0:
            return
        hard_limit_hit = duration + 1e-9 >= self.policy.max_segment_sec
        soft_limit_hit = (
            self.policy.soft_text_chars > 0
            and duration + 1e-9 >= self.policy.min_segment_sec
            and len(session.active_partial_text.strip()) >= self.policy.soft_text_chars
        )
        if hard_limit_hit or soft_limit_hit:
            reason = "hard_duration" if hard_limit_hit else "soft_text_chars"
            self._commit_active_segment(session, simulated_now_ms=simulated_now_ms, reason=reason)

    def _commit_active_segment(
        self,
        session: SegmentedSessionState,
        *,
        simulated_now_ms: float,
        reason: str,
    ) -> SegmentRecord | None:
        active_audio = session.active_audio
        if len(active_audio) == 0:
            return None
        audio_start_ms = session.active_segment_start_ms
        audio_end_ms = audio_start_ms + len(active_audio) / float(SAMPLE_RATE) * 1000.0
        cache_path = session.segment_cache_path()
        ready_ms = max(simulated_now_ms, audio_end_ms, self.worker_available_ms)
        result = self.backend.final(active_audio)
        committed_ms = ready_ms + result.wall_ms
        self.worker_available_ms = committed_ms
        record = SegmentRecord(
            index=session.active_segment_index,
            audio_start_ms=audio_start_ms,
            audio_end_ms=audio_end_ms,
            sample_count=int(len(active_audio)),
            cache_path=cache_path,
            final_text=result.text,
            compute_wall_ms=result.wall_ms,
            committed_offset_ms=committed_ms,
            mode=result.mode,
        )
        session.committed_segments.append(record)
        session.active_chunks = []
        session.active_partial_text = ""
        session.active_segment_index += 1
        session.active_segment_start_ms = audio_end_ms
        session.active_next_prefix_sec = self.policy.partial_step_sec
        session.active_emitted_prefix_count = 0
        self._append_event(
            {
                "kind": "segment_final",
                "session_id": session.session_id,
                "session_token": session.token,
                "recv_offset_ms": committed_ms,
                "ready_offset_ms": ready_ms,
                "compute_wall_ms": result.wall_ms,
                "reason": reason,
                "segment": record.public_dict(),
                "is_final": False,
                "accepted": False,
            }
        )
        if session.status == "recording":
            session.revision += 1
            self._emit_visible_partial(
                session,
                text=session.committed_text,
                recv_offset_ms=committed_ms,
                ready_offset_ms=ready_ms,
                compute_wall_ms=result.wall_ms,
                audio_end_ms=audio_end_ms,
                mode="segment_commit_partial",
            )
        return record

    def _emit_visible_partial(
        self,
        session: SegmentedSessionState,
        *,
        text: str,
        recv_offset_ms: float,
        ready_offset_ms: float,
        compute_wall_ms: float,
        audio_end_ms: float,
        mode: str,
    ) -> dict[str, Any]:
        return self._append_event(
            {
                "kind": "partial",
                "session_id": session.session_id,
                "session_token": session.token,
                "revision": session.revision,
                "recv_offset_ms": recv_offset_ms,
                "ready_offset_ms": ready_offset_ms,
                "compute_wall_ms": compute_wall_ms,
                "audio_end_ms": audio_end_ms,
                "mode": mode,
                "text": text,
                "meaningful_text": bool(text.strip()),
                "segment_count": len(session.committed_segments),
                "is_final": False,
                "accepted": True,
            }
        )

    def _current_recording_session(
        self,
        session_id: str,
        *,
        session_token: int | None,
        recv_offset_ms: float,
        ignored_kind: str,
    ) -> SegmentedSessionState | None:
        session = self._current_session(
            session_id,
            session_token=session_token,
            recv_offset_ms=recv_offset_ms,
            ignored_kind=ignored_kind,
        )
        if session is None:
            return None
        if session.status != "recording":
            self._append_ignored(
                kind=ignored_kind,
                session_id=session_id,
                session_token=session_token,
                current_session_token=session.token,
                recv_offset_ms=recv_offset_ms,
                reason=f"session_not_recording:{session.status}",
            )
            return None
        return session

    def _current_session(
        self,
        session_id: str,
        *,
        session_token: int | None,
        recv_offset_ms: float,
        ignored_kind: str,
    ) -> SegmentedSessionState | None:
        session = self.sessions.get(session_id)
        if session is None:
            self._append_ignored(
                kind=ignored_kind,
                session_id=session_id,
                session_token=session_token,
                recv_offset_ms=recv_offset_ms,
                reason="missing_session",
            )
            return None
        if session_token is not None and session.token != session_token:
            self._append_ignored(
                kind=ignored_kind,
                session_id=session_id,
                session_token=session_token,
                current_session_token=session.token,
                recv_offset_ms=recv_offset_ms,
                reason="session_token_mismatch",
            )
            return None
        return session

    def _append_ignored(self, **event: Any) -> dict[str, Any]:
        event.setdefault("accepted", False)
        event.setdefault("is_final", False)
        return self._append_event(event)

    def _append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event.setdefault("recv_epoch_ms", now_ms())
        self.events.append(event)
        return event

    def _allocate_token(self) -> int:
        token = self._next_token
        self._next_token += 1
        return token

    def _write_session_metadata(self, session: SegmentedSessionState) -> None:
        cache_bytes = 0
        if session.session_audio_path.exists():
            cache_bytes = session.session_audio_path.stat().st_size
        write_json(
            session.metadata_path,
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "session_id": session.session_id,
                "session_token": session.token,
                "status": session.status,
                "sample_rate": SAMPLE_RATE,
                "sample_format": "float32_le",
                "cache_dir": str(session.cache_dir),
                "session_audio_path": str(session.session_audio_path),
                "cache_bytes": cache_bytes,
                "segment_policy": policy_dict(self.policy),
                "committed_segments": [segment.public_dict() for segment in session.committed_segments],
                "active_segment_index": session.active_segment_index,
                "active_duration_seconds": round3(session.active_duration_seconds),
                "final_text": session.final_text,
                "merge_strategy": "zero_overlap_concat",
                "updated_epoch_ms": now_ms(),
            },
        )


class SegmentedHttpState:
    def __init__(
        self,
        *,
        service: SegmentedCacheService,
        backend: Any,
        model_info: dict[str, Any],
        model_surface: dict[str, Any],
        fake_backend: bool,
        model_load_wall_ms: float,
    ) -> None:
        self.lock = threading.RLock()
        self.service = service
        self.backend = backend
        self.fake_backend = fake_backend
        self.expected_text_by_session: dict[str, str] = {}
        self.model_info = model_info
        self.model_surface = model_surface
        self.model_load_wall_ms = model_load_wall_ms
        self.started_epoch_ms = now_ms()

    def metadata(self) -> dict[str, Any]:
        return {
            "schema_version": SERVICE_SCHEMA_VERSION,
            "service": "qwen3-mlx-segmented-cache-service",
            "fake_backend": self.fake_backend,
            "native_realtime_gate_eligible": False,
            "model_info": self.model_info,
            "model_surface": self.model_surface,
            "model_load_wall_ms": self.model_load_wall_ms,
            "started_epoch_ms": self.started_epoch_ms,
            "contract": ["start", "chunk", "finish", "cancel"],
            "segment_policy": policy_dict(self.service.policy),
        }

    def start(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        with self.lock:
            session_id = str(payload["session_id"])
            expected_text = str(payload.get("expected_text", "")).strip()
            if expected_text:
                self.expected_text_by_session[session_id] = expected_text
            self._select_fake_expected_text(session_id)
            before = len(self.service.events)
            self.service.start(
                session_id,
                session_token=int(payload["session_token"]) if "session_token" in payload else None,
                simulated_now_ms=float(payload.get("recv_offset_ms", 0.0)),
            )
            return public_events(self.service.events[before:])

    def chunk(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        with self.lock:
            session_id = str(payload["session_id"])
            self._select_fake_expected_text(session_id)
            before = len(self.service.events)
            pcm = pcm16_base64_to_float32(payload)
            self.service.push_pcm(
                session_id,
                pcm,
                session_token=int(payload["session_token"]) if "session_token" in payload else None,
                simulated_now_ms=float(payload.get("recv_offset_ms", payload.get("audio_end_ms", 0.0))),
                audio_start_ms=float(payload.get("audio_start_ms", 0.0)),
                audio_end_ms=float(payload.get("audio_end_ms", 0.0)),
                chunk_index=int(payload.get("chunk_index", 0)),
            )
            return public_events(self.service.events[before:])

    def finish(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        with self.lock:
            session_id = str(payload["session_id"])
            self._select_fake_expected_text(session_id)
            before = len(self.service.events)
            self.service.finish(
                session_id,
                session_token=int(payload["session_token"]) if "session_token" in payload else None,
                simulated_now_ms=float(payload.get("recv_offset_ms", 0.0)),
            )
            return public_events(self.service.events[before:])

    def cancel(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        with self.lock:
            before = len(self.service.events)
            self.service.cancel(
                str(payload["session_id"]),
                session_token=int(payload["session_token"]) if "session_token" in payload else None,
                simulated_now_ms=float(payload.get("recv_offset_ms", 0.0)),
            )
            return public_events(self.service.events[before:])

    def _select_fake_expected_text(self, session_id: str) -> None:
        if isinstance(self.backend, ExpectedTextFakeBackend):
            self.backend.set_expected_text(self.expected_text_by_session.get(session_id, ""))


class SegmentedHttpHandler(BaseHTTPRequestHandler):
    state: SegmentedHttpState

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/metadata"}:
            self._write_json({"ok": True, **self.state.metadata()})
            return
        self._write_json({"error": f"unknown path: {self.path}"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_payload()
            if self.path == "/start":
                events = self.state.start(payload)
            elif self.path == "/chunk":
                events = self.state.chunk(payload)
            elif self.path == "/finish":
                events = self.state.finish(payload)
            elif self.path == "/cancel":
                events = self.state.cancel(payload)
            else:
                self._write_json({"error": f"unknown path: {self.path}"}, status=404)
                return
            self._write_json({"events": events, "metadata": self.state.metadata()})
        except Exception as exc:  # pragma: no cover - surfaced in integration tests
            traceback.print_exc()
            self._write_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def _read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _write_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def pcm16_base64_to_float32(payload: dict[str, Any]) -> np.ndarray:
    sample_rate = int(payload.get("sample_rate", SAMPLE_RATE))
    channels = int(payload.get("channels", 1))
    sample_width = int(payload.get("sample_width_bytes", 2))
    if sample_rate != SAMPLE_RATE or channels != 1 or sample_width != 2:
        raise ValueError("expected 16 kHz mono int16 PCM chunks")
    raw_b64 = str(payload.get("pcm_base64", ""))
    if not raw_b64:
        return np.zeros((0,), dtype=np.float32)
    raw = base64.b64decode(raw_b64.encode("ascii"), validate=True)
    if len(raw) % 2:
        raise ValueError("pcm_base64 decoded byte count must be divisible by 2 for int16 PCM")
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def public_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for event in events:
        kind = str(event.get("kind", ""))
        if kind in {"partial", "final"} or kind.startswith("ignored"):
            result.append(event)
    return result


def wav_pcm_float32(audio_path: Path) -> tuple[np.ndarray, float]:
    wav = read_wav_16k_mono_int16(audio_path)
    pcm = np.frombuffer(wav.pcm, dtype="<i2").astype(np.float32) / 32768.0
    return pcm, wav.duration_seconds


def run_service_case(
    *,
    case: Any,
    service: SegmentedCacheService,
    out_dir: Path,
    chunk_ms: int,
    model_info: dict[str, Any],
    fake_backend: bool,
    max_first_usable_partial_ms: float,
    max_final_latency_ms: float,
    max_final_cer: float,
) -> dict[str, Any]:
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    chunks_path = case_out / "chunks.jsonl"
    for path in (events_path, chunks_path):
        if path.exists():
            path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    if isinstance(service.backend, ExpectedTextFakeBackend):
        service.backend.set_expected_text(case.expected_text)

    pcm, duration_seconds = wav_pcm_float32(case.audio_path)
    stride = max(1, int(SAMPLE_RATE * chunk_ms / 1000.0))
    session_id = case.case_id
    token = service.start(session_id, simulated_now_ms=0.0)
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
            session_token=token,
            simulated_now_ms=audio_end_ms,
            audio_start_ms=audio_start_ms,
            audio_end_ms=audio_end_ms,
            chunk_index=index,
        )
    input_finished_offset_ms = duration_seconds * 1000.0
    service.finish(session_id, session_token=token, simulated_now_ms=input_finished_offset_ms)

    case_events = [e for e in service.events if e.get("session_id") == session_id]
    for event in case_events:
        append_jsonl(events_path, event)

    final_events = [e for e in case_events if e.get("kind") == "final" and e.get("text")]
    final_text = str(final_events[-1].get("text", "")) if final_events else ""
    gate_expected_text = final_text if fake_backend and final_text else case.expected_text
    gate = evaluate_service_gate(
        events=case_events,
        expected_text=gate_expected_text,
        input_finished_offset_ms=input_finished_offset_ms,
        max_first_usable_partial_ms=max_first_usable_partial_ms,
        max_final_latency_ms=max_final_latency_ms,
        max_final_cer=max_final_cer,
    )
    partial_texts = [str(e.get("text", "")) for e in case_events if e.get("kind") == "partial" and e.get("text")]
    segment_finals = [e for e in case_events if e.get("kind") == "segment_final"]
    session = service.sessions.get(session_id)
    cache_bytes = 0
    if session is not None and session.session_audio_path.exists():
        cache_bytes = session.session_audio_path.stat().st_size
    summary = {
        "schema_version": SERVICE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "case_id": case.case_id,
        "model_info": model_info,
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "audio": str(case.audio_path),
        "duration_seconds": duration_seconds,
        "input_finished_offset_ms": input_finished_offset_ms,
        "chunk_ms": chunk_ms,
        "chunk_count": len(chunk_records),
        "lang": case.lang,
        "scenario": case.scenario,
        "expected_text": case.expected_text,
        "fake_backend": fake_backend,
        "service_contract": ["start", "chunk", "partial", "segment_final", "finish", "final", "cancel"],
        "segment_policy": policy_dict(service.policy),
        "segment_count": len(segment_finals),
        "cache_dir": str(session.cache_dir) if session is not None else None,
        "cache_bytes": cache_bytes,
        "gate": gate,
        "final_text": final_text,
        "cer": None if fake_backend else cer(case.expected_text, final_text),
        "wer": None if fake_backend else wer(case.expected_text, final_text),
        "coverage": char_length_ratio(final_text, case.expected_text),
        "partial_event_count": len([e for e in case_events if e.get("kind") == "partial"]),
        "final_event_count": len(final_events),
        "event_count": len(case_events),
        "partial_rewrite_rate": partial_rewrite_rate(partial_texts),
        "native_realtime_gate_eligible": False,
        "wrapper_service_candidate": gate["service_gate_passed"],
    }
    write_json(case_out / "summary.json", summary)
    return summary


def command_run(args: argparse.Namespace) -> int:
    cases = filter_cases(load_cases(Path(args.cases), allow_missing_audio=False), args.case_id)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)
    policy = policy_from_args(args)

    load_started = time.perf_counter()
    if args.fake_backend:
        backend = ExpectedTextFakeBackend()
        model_surface = {"fake_backend": True}
    else:
        model = load_mlx_model(args.model, args.mlx_audio_source)
        backend = MLXBackend(model, language=args.language.strip() or None, max_tokens=args.max_tokens)
        model_surface = classify_model_surface(model)
    load_wall_ms = (time.perf_counter() - load_started) * 1000.0

    service = SegmentedCacheService(
        backend=backend,
        policy=policy,
        spool_dir=Path(args.spool_dir),
    )
    case_summaries = [
        run_service_case(
            case=case,
            service=service,
            out_dir=out_dir,
            chunk_ms=args.chunk_ms,
            model_info=model_info,
            fake_backend=args.fake_backend,
            max_first_usable_partial_ms=args.max_first_usable_partial_ms,
            max_final_latency_ms=args.max_final_latency_ms,
            max_final_cer=args.max_final_cer,
        )
        for case in cases
    ]
    service_passes = [bool(summary["gate"]["service_gate_passed"]) for summary in case_summaries]
    summary = {
        "schema_version": SERVICE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "model": args.model,
        "model_id": args.model_id,
        "model_info": model_info,
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "api_surface": model_surface,
        "model_load_wall_ms": load_wall_ms,
        "fake_backend": args.fake_backend,
        "segment_policy": policy_dict(policy),
        "case_count": len(case_summaries),
        "case_ids": [summary["case_id"] for summary in case_summaries],
        "aggregate_status": "all_cases_passed" if all(service_passes) else "mixed_or_failed_cases",
        "native_realtime_gate_eligible": False,
        "wrapper_service_candidate": all(service_passes),
        "case_summaries": case_summaries,
        "final_recommendation": {
            "wire_into_app_now": False,
            "reason": (
                "This validates a service-side segmented-cache prototype. "
                "Swift App integration needs a separate spec and manual safety validation."
            ),
        },
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if all(service_passes) else 1


def command_self_test(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="qwen3-segmented-cache-test-") as tmp:
        policy = SegmentPolicy(
            max_segment_sec=1.2,
            min_segment_sec=0.5,
            soft_text_chars=0,
            partial_step_sec=0.5,
            max_partials_per_segment=4,
        )
        backend = ExpectedTextFakeBackend()
        backend.set_expected_text("这是一个分段缓存服务测试。")
        service = SegmentedCacheService(backend=backend, policy=policy, spool_dir=Path(tmp))
        token = service.start("session", simulated_now_ms=0.0)
        stride = int(SAMPLE_RATE * 0.4)
        for index in range(5):
            start_ms = index * 400.0
            end_ms = start_ms + 400.0
            service.push_pcm(
                "session",
                np.zeros((stride,), dtype=np.float32),
                session_token=token,
                simulated_now_ms=end_ms,
                audio_start_ms=start_ms,
                audio_end_ms=end_ms,
                chunk_index=index,
            )
        service.finish("session", session_token=token, simulated_now_ms=2000.0)
        events = [event for event in service.events if event.get("session_id") == "session"]
        if not any(event.get("kind") == "segment_final" and event.get("reason") == "hard_duration" for event in events):
            raise AssertionError(f"expected a hard-duration segment commit: {events}")
        finals = [event for event in events if event.get("kind") == "final" and event.get("accepted") is True]
        if len(finals) != 1:
            raise AssertionError(f"expected exactly one accepted final: {events}")
        session = service.sessions["session"]
        if not session.session_audio_path.exists() or session.session_audio_path.stat().st_size == 0:
            raise AssertionError("session audio cache was not written")
        if not session.metadata_path.exists():
            raise AssertionError("session metadata was not written")
        gate = evaluate_service_gate(
            events=events,
            expected_text=str(finals[-1]["text"]),
            input_finished_offset_ms=2000.0,
            max_first_usable_partial_ms=1500.0,
            max_final_latency_ms=2500.0,
            max_final_cer=0.0,
        )
        if not gate["service_gate_passed"]:
            raise AssertionError(f"fake segmented service gate failed: {gate}")

        stale_service = SegmentedCacheService(
            backend=ExpectedTextFakeBackend(),
            policy=policy,
            spool_dir=Path(tmp),
        )
        old_token = stale_service.start("same", simulated_now_ms=0.0)
        new_token = stale_service.start("same", simulated_now_ms=10.0)
        stale_service.push_pcm(
            "same",
            np.zeros((stride,), dtype=np.float32),
            session_token=old_token,
            simulated_now_ms=500.0,
            audio_start_ms=0.0,
            audio_end_ms=500.0,
            chunk_index=0,
        )
        stale_service.finish("same", session_token=new_token, simulated_now_ms=500.0)
        if not any(event.get("kind") == "ignored_stale_chunk" for event in stale_service.events):
            raise AssertionError(f"missing stale chunk rejection: {stale_service.events}")

        cancel_service = SegmentedCacheService(
            backend=ExpectedTextFakeBackend(),
            policy=policy,
            spool_dir=Path(tmp),
        )
        cancel_token = cancel_service.start("cancel", simulated_now_ms=0.0)
        cancel_service.cancel("cancel", session_token=cancel_token, simulated_now_ms=100.0)
        cancel_service.finish("cancel", session_token=cancel_token, simulated_now_ms=200.0)
        if any(event.get("kind") == "final" and event.get("accepted") is True for event in cancel_service.events):
            raise AssertionError(f"cancel leaked final output: {cancel_service.events}")

    print("Qwen3 MLX segmented-cache service self-test passed.")
    return 0


def command_serve(args: argparse.Namespace) -> int:
    state = build_http_state(args)
    SegmentedHttpHandler.state = state
    server = HTTPServer((args.host, args.port), SegmentedHttpHandler)
    print(
        json.dumps(
            {
                "ok": True,
                "listening": f"http://{args.host}:{args.port}",
                "metadata": state.metadata(),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def build_http_state(args: argparse.Namespace) -> SegmentedHttpState:
    model_info = load_model_metadata(Path(args.registry), args.model_id)
    load_started = time.perf_counter()
    if args.fake_backend:
        backend = ExpectedTextFakeBackend()
        model_surface = {"fake_backend": True}
    else:
        model = load_mlx_model(args.model, args.mlx_audio_source)
        backend = MLXBackend(model, language=args.language.strip() or None, max_tokens=args.max_tokens)
        model_surface = classify_model_surface(model)
    load_wall_ms = (time.perf_counter() - load_started) * 1000.0
    service = SegmentedCacheService(
        backend=backend,
        policy=policy_from_args(args),
        spool_dir=Path(args.spool_dir),
    )
    return SegmentedHttpState(
        service=service,
        backend=backend,
        model_info=model_info,
        model_surface=model_surface,
        fake_backend=args.fake_backend,
        model_load_wall_ms=load_wall_ms,
    )


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


def policy_from_args(args: argparse.Namespace) -> SegmentPolicy:
    return SegmentPolicy(
        max_segment_sec=float(args.max_segment_sec),
        min_segment_sec=float(args.min_segment_sec),
        soft_text_chars=int(args.soft_text_chars),
        partial_step_sec=float(args.partial_step_sec),
        max_partials_per_segment=int(args.max_partials_per_segment),
    )


def append_float32(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as f:
        f.write(np.asarray(audio, dtype="<f4").tobytes())


def join_text_parts(parts: list[str]) -> str:
    return "".join(part for part in parts if part)


def safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned[:120] or "session"


def policy_dict(policy: SegmentPolicy) -> dict[str, Any]:
    return {
        "max_segment_sec": policy.max_segment_sec,
        "min_segment_sec": policy.min_segment_sec,
        "soft_text_chars": policy.soft_text_chars,
        "partial_step_sec": policy.partial_step_sec,
        "max_partials_per_segment": policy.max_partials_per_segment,
    }


def round3(value: float) -> float:
    return round(float(value), 3)


def add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=".external/models/mlx-community__Qwen3-ASR-0.6B-8bit")
    parser.add_argument("--model-id", default="qwen3-asr-0.6b-mlx-8bit")
    parser.add_argument("--mlx-audio-source", default=".external/repos/mlx-audio")
    parser.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--fake-backend", action="store_true")
    parser.add_argument("--spool-dir", default=str(DEFAULT_SPOOL_DIR))
    parser.add_argument("--max-segment-sec", type=float, default=30.0)
    parser.add_argument("--min-segment-sec", type=float, default=5.0)
    parser.add_argument("--soft-text-chars", type=int, default=150)
    parser.add_argument("--partial-step-sec", type=float, default=1.0)
    parser.add_argument("--max-partials-per-segment", type=int, default=8)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    self_test = sub.add_parser("self-test", help="Run service self-tests without model weights.")
    self_test.set_defaults(func=command_self_test)

    run = sub.add_parser("run", help="Run segmented-cache service against local WAV cases.")
    add_common_runtime_args(run)
    run.add_argument("--cases", default="eval/asr_streaming/cases.smoke.local.jsonl")
    run.add_argument("--case-id", action="append", default=[], help="Case id; repeatable or comma-separated.")
    run.add_argument("--chunk-ms", type=int, default=100)
    run.add_argument("--max-first-usable-partial-ms", type=float, default=2500.0)
    run.add_argument("--max-final-latency-ms", type=float, default=2500.0)
    run.add_argument("--max-final-cer", type=float, default=0.15)
    run.add_argument("--out-dir", default="eval/asr_streaming/results/qwen3-mlx-segmented-cache-service")
    run.set_defaults(func=command_run)

    serve = sub.add_parser("serve", help="Serve the segmented-cache service over localhost JSON HTTP.")
    add_common_runtime_args(serve)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=18096)
    serve.set_defaults(func=command_serve)

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
