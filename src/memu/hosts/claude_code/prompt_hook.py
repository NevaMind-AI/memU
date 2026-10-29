"""Claude UserPromptSubmit retrieval through the installed shared adapter."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from memu import events
from memu.env import LONG_QUERY_CHARS, QueryKind
from memu.hosts.retrieval import retrieve

CONTEXT_BUDGET = 9500


def _context(result: dict[str, Any]) -> str:
    """Keep status visible while bounding Claude's UTF-16 hook context."""
    selected = {**result, "hits": [], "resources": []}
    prefix = "memU retrieval completed successfully (score filtering is heuristic). Reference data:\n"

    def render() -> str:
        return prefix + json.dumps(selected, ensure_ascii=False, separators=(",", ":"))

    for layer in ("hits", "resources"):
        for item in result.get(layer, []):
            selected[layer].append(item)
            if len(render().encode("utf-16-le")) // 2 > CONTEXT_BUDGET:
                selected[layer].pop()
    selected["context_counts"] = {layer: len(selected[layer]) for layer in ("hits", "resources")}
    # Reserve space for the final counts before returning the bounded context.
    while len(render().encode("utf-16-le")) // 2 > CONTEXT_BUDGET:
        layer = "resources" if selected["resources"] else "hits"
        if not selected[layer]:
            raise ValueError("retrieval status exceeds context budget")  # noqa: TRY003
        selected[layer].pop()
        selected["context_counts"][layer] = len(selected[layer])
    return render()


def _read_event() -> tuple[dict[str, Any], str]:
    event = json.load(sys.stdin)
    if not isinstance(event, dict) or event.get("hook_event_name") != "UserPromptSubmit":
        raise ValueError("expected UserPromptSubmit object")  # noqa: TRY003
    prompt = event.get("prompt")
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")  # noqa: TRY003
    return event, prompt


async def _cmd_prompt_hook(args: argparse.Namespace) -> int:
    started = time.monotonic()
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")
    trace: dict[str, Any] = {"status": "started"}
    try:
        event, prompt = _read_event()
        trace.update(session_id=event.get("session_id"), prompt_chars=len(prompt))
        if os.environ.get("MEMU_CLAUDE_MEMORIZE") == "1":
            trace["status"] = "self_run_skipped"
            return 0
        if not prompt.strip():
            trace["status"] = "empty_prompt"
            return 0
        trace["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        # Classify from the original prompt before bounding the transported query.
        kind: QueryKind = "long" if sum(not c.isspace() for c in prompt) >= LONG_QUERY_CHARS else "short"
        result = await asyncio.wait_for(retrieve(prompt[:2000], query_kind=kind), timeout=40)
        context = _context(result)
        trace.update(status="context_returned", retrieve_result=result, additional_context=context)
        print(
            json.dumps(
                {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}},
                ensure_ascii=False,
            )
        )
        events.record_outcome(
            events.MEMORY_SEARCH_SUCCEEDED,
            events.MEMORY_SEARCH_FAILED,
            host="claude-code",
            session_id_env="CLAUDE_CODE_SESSION_ID",
            success=True,
            deliver=True,
            result_count=events.counts(result, layers=("hits", "resources")),
            latency_ms=round((time.monotonic() - started) * 1000),
        )
    except Exception as exc:
        trace.update(status="failed", error=str(exc))
        print(f"memU retrieve hook failed: {exc}", file=sys.stderr)
    finally:
        trace["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        base = Path(args.base_dir).expanduser() if args.base_dir else Path.home() / ".memu/hosts/claude-code"
        directory = base / "log/hooks/retrieve"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{uuid4()}.json").write_text(
                json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            print(f"memU retrieve hook log failed: {exc}", file=sys.stderr)
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("prompt-hook", help="Retrieve memory for a Claude UserPromptSubmit event")
    parser.add_argument("--base-dir", default=None, help="Host state directory for hook logs")
    parser.set_defaults(handler=_cmd_prompt_hook)
