#!/usr/bin/env python3
"""Probe the community mlx-qwen3-asr streaming surface.

This is an evidence-gathering entry point. It separates package/project claims
from local proof that LocalVoiceInput can feed timed PCM chunks into a stable
session API.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "1.0"

MODULE_CANDIDATES = [
    "mlx_qwen3_asr",
    "mlx_qwen3_asr.session",
    "mlx_qwen3_asr.streaming",
    "mlx_qwen3_asr.server",
    "mlx_qwen3_asr.transcribe",
    "qwen3_asr_mlx",
    "qwen3_asr",
    "mlx_qwen3",
]

SESSION_KEYWORDS = [
    "create_streaming_session",
    "feed",
    "step",
    "close",
    "push_pcm",
    "streaming",
    "kv_cache",
    "cache",
    "context_trim",
    "tail_refine",
    "tail_refinement",
]

METRIC_EXPLANATIONS_ZH = {
    "incremental_pcm_feed": "是否能持续接收麦克风 PCM 小块，而不是每次传完整音频文件。",
    "state_cache_reuse": "是否复用模型内部状态或 KV cache，避免从第 0 秒无限重算。",
    "tail_refinement": "是否只允许最近尾部文本继续修正，而不是整段文本反复覆盖。",
    "true_session_streaming": "是否存在 start/feed/step-or-read/finish/cancel 风格的会话接口。",
    "claim_vs_verified": "区分 README 或模型卡声称和本机代码/API 实际验证结果。",
}


def now_ms() -> int:
    return int(time.time() * 1000)


def safe_signature(obj: Any) -> str | None:
    try:
        return str(inspect.signature(obj))
    except Exception as exc:
        return f"<signature unavailable: {exc}>"


def public_members(obj: Any) -> dict[str, Any]:
    members: dict[str, Any] = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        lowered = name.lower()
        if not any(keyword in lowered for keyword in SESSION_KEYWORDS):
            continue
        value = getattr(obj, name, None)
        members[name] = {
            "type": type(value).__name__,
            "callable": callable(value),
            "signature": safe_signature(value) if callable(value) else None,
        }
    return members


def import_modules(source_dir: Path | None) -> list[dict[str, Any]]:
    if source_dir and source_dir.exists():
        sys.path.insert(0, str(source_dir.resolve()))
    results: list[dict[str, Any]] = []
    for module_name in MODULE_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            results.append(
                {
                    "module": module_name,
                    "imported": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        results.append(
            {
                "module": module_name,
                "imported": True,
                "module_file": getattr(module, "__file__", None),
                "members": public_members(module),
            }
        )
    return results


def scan_source(source_dir: Path | None, *, max_files: int = 200) -> dict[str, Any]:
    if source_dir is None or not source_dir.exists():
        return {
            "source_dir": str(source_dir) if source_dir else None,
            "exists": False,
            "keyword_hits": [],
        }
    hits: list[dict[str, Any]] = []
    scanned = 0
    for path in sorted(source_dir.rglob("*.py")):
        if scanned >= max_files:
            break
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lowered = text.lower()
        matched = [keyword for keyword in SESSION_KEYWORDS if keyword in lowered]
        if matched:
            hits.append(
                {
                    "path": str(path),
                    "keywords": matched,
                }
            )
    return {
        "source_dir": str(source_dir),
        "exists": True,
        "git_commit": git_commit(source_dir),
        "scanned_python_files": scanned,
        "keyword_hits": hits[:50],
        "truncated": len(hits) > 50,
    }


def git_commit(source_dir: Path) -> str | None:
    if not (source_dir / ".git").exists():
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


def classify(import_results: list[dict[str, Any]], source_scan: dict[str, Any]) -> dict[str, Any]:
    imported_modules = [result for result in import_results if result.get("imported")]
    member_names: set[str] = set()
    for result in imported_modules:
        for name in (result.get("members") or {}).keys():
            member_names.add(name.lower())

    keyword_hits = source_scan.get("keyword_hits") or []
    source_keywords: set[str] = set()
    for hit in keyword_hits:
        for keyword in hit.get("keywords") or []:
            source_keywords.add(str(keyword).lower())

    has_session_like_members = any(
        key in member_names
        for key in {
            "create_streaming_session",
            "init_streaming",
            "feed_audio",
            "finish_streaming",
            "streamingstate",
            "push_pcm",
            "feed",
            "step",
            "close",
        }
    )
    has_cache_claim_surface = bool({"kv_cache", "cache"} & source_keywords) or any(
        "cache" in name for name in member_names
    )
    has_tail_surface = bool({"tail_refine", "tail_refinement"} & source_keywords) or any(
        "tail" in name for name in member_names
    )

    verified = False
    reason = "missing_imported_session_api"
    if has_session_like_members:
        reason = "session_like_members_present_but_needs_pcm_smoke"
    if not imported_modules and keyword_hits:
        reason = "source_keywords_present_but_package_not_imported"
    if not imported_modules and not keyword_hits:
        reason = "package_or_source_not_available"

    return {
        "claim_vs_verified": {
            "claims_checked": [
                "streaming KV/cache support",
                "context trimming",
                "tail refinement",
                "long audio",
            ],
            "locally_verified_true_streaming": verified,
            "reason": reason,
        },
        "surface_signals": {
            "imported_module_count": len(imported_modules),
            "session_like_members_present": has_session_like_members,
            "cache_keyword_or_member_present": has_cache_claim_surface,
            "tail_keyword_or_member_present": has_tail_surface,
            "source_keyword_hit_count": len(keyword_hits),
        },
        "realtime_gate_eligible_now": False,
        "next_validation_needed": [
            "identify exact package/module entry point",
            "load Qwen3-ASR MLX model through this package",
            "feed timed 16 kHz mono PCM chunks without materializing full audio",
            "prove partial before stop and final after stop",
            "prove cancel and stale-session isolation",
            "measure long-dictation latency and text churn",
        ],
    }


def command_run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = Path(args.source_dir) if args.source_dir else None

    if args.dry_run:
        import_results: list[dict[str, Any]] = []
        source_scan = {
            "source_dir": str(source_dir) if source_dir else None,
            "exists": bool(source_dir and source_dir.exists()),
            "keyword_hits": [],
            "dry_run": True,
        }
    else:
        import_results = import_modules(source_dir)
        source_scan = scan_source(source_dir)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "probe": "mlx-qwen3-asr-streaming-surface",
        "dry_run": bool(args.dry_run),
        "source_dir": str(source_dir) if source_dir else None,
        "package_url": "https://github.com/moona3k/mlx-qwen3-asr/",
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "import_results": import_results,
        "source_scan": source_scan,
        "classification": classify(import_results, source_scan),
    }
    path = out_dir / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=".external/repos/mlx-qwen3-asr")
    parser.add_argument("--out-dir", default="eval/asr_streaming/results/mlx-qwen3-asr-streaming-probe")
    parser.add_argument("--dry-run", action="store_true")
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
