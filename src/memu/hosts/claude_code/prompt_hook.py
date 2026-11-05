"""Claude Submit retrieval with a whole-entry context budget."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from memu.env import LONG_QUERY_CHARS
from memu.hosts.claude_code.query_extraction import select_query
from memu.hosts.claude_code.submit import is_automatic
from memu.hosts.retrieval import CONTEXT_PREFIX as CONTEXT_PREFIX
from memu.hosts.retrieval import render_context

LAYERS = ("hits", "resources")
CONTEXT_BUDGET = 9500


def bounded_context(memories: dict[str, Any], trace: dict[str, Any]) -> str | None:
    """Keep complete entries within Claude's limit, including prefix and JSON."""
    selected: dict[str, Any] = {layer: [] for layer in LAYERS}
    if "retrieval_status" in memories:
        selected["retrieval_status"] = memories["retrieval_status"]

    def render() -> str:
        return render_context(selected, original=memories)

    def units(text: str) -> int:
        # Count JavaScript string units conservatively: emoji can consume two.
        return len(text.encode("utf-16-le", errors="surrogatepass")) // 2

    for layer in LAYERS:
        for item in memories.get(layer, []):
            if not isinstance(item, dict):
                raise TypeError("retrieve entries must be objects")  # noqa: TRY003
            selected[layer].append(item)
            if units(render()) > CONTEXT_BUDGET:
                selected[layer].pop()
    context = render()
    trace.update(
        context_chars=len(context),
        context_utf16_units=units(context),
        context_budget=CONTEXT_BUDGET,
        returned_counts={layer: len(selected[layer]) for layer in LAYERS},
        omitted_counts={layer: len(memories.get(layer, [])) - len(selected[layer]) for layer in LAYERS},
    )
    if units(context) > CONTEXT_BUDGET:
        return None
    return context if any(selected.values()) or not any(memories.get(layer) for layer in LAYERS) else None


def _retrieve(trace: dict[str, Any]) -> dict[str, Any] | None:  # noqa: C901
    event = json.load(sys.stdin)
    if not isinstance(event, dict) or event.get("hook_event_name") != "UserPromptSubmit":
        raise ValueError("expected a UserPromptSubmit object")  # noqa: TRY003
    if is_automatic(event):
        trace["status"] = "automatic_event_skipped"
        return None
    prompt = event.get("prompt")
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")  # noqa: TRY003
    trace.update(session_id=event.get("session_id"), prompt_chars=len(prompt))
    if os.environ.get("MEMU_CLAUDE_MEMORIZE") == "1":
        trace["status"] = "self_run_skipped"
        return None
    if not prompt.strip():
        trace["status"] = "empty_query"
        return None
    started = time.monotonic()
    query = select_query(prompt, trace)
    query_kind = (
        "extracted"
        if trace["query_source"] == "extracted"
        else "long"
        if sum(not char.isspace() for char in prompt) >= LONG_QUERY_CHARS
        else "short"
    )
    trace.update(
        query=query,
        query_kind=query_kind,
        query_chars=len(query),
        query_truncated=trace["query_source"] == "prefix",
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    )
    if not query.strip():
        trace["status"] = "empty_query"
        return None
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if isinstance(event.get("session_id"), str):
        env["CLAUDE_CODE_SESSION_ID"] = event["session_id"]
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "memu.hosts.claude_code.cli", "retrieve", "--query-stdin", "--query-kind", query_kind],
        input=query.encode("utf-8"),
        capture_output=True,
        timeout=max(1, 40 - (time.monotonic() - started)),
        env=env,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    trace["retrieve_exit_code"] = result.returncode
    if result.returncode:
        trace.update(status="failed", stderr=result.stderr.decode("utf-8", errors="replace"))
        return None
    memories = json.loads(result.stdout.decode("utf-8"))
    if not isinstance(memories, dict) or any(not isinstance(memories.get(k, []), list) for k in LAYERS):
        raise ValueError("retrieve must return an object containing result lists")  # noqa: TRY003
    trace["retrieve_result"] = memories
    trace["counts"] = {k: len(memories.get(k, [])) for k in LAYERS}
    context = bounded_context(memories, trace)
    trace["additional_context"] = context
    if context is None:
        trace["status"] = "budget_exhausted"
        return None
    trace["status"] = "context_returned" if any(trace["counts"].values()) else "empty_result"
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}


async def _cmd_prompt_hook(args: argparse.Namespace) -> int:
    started = time.monotonic()
    trace: dict[str, Any] = {"observed_at": datetime.now(UTC).isoformat(), "status": "started", "pid": os.getpid()}
    output = None
    try:
        output = _retrieve(trace)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        trace.update(status="failed", error=str(exc))
    trace["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    try:
        base = Path(args.base_dir).expanduser() if args.base_dir else Path.home() / ".memu/hosts/claude-code"
        directory = base / "log/hooks/retrieve"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{uuid4()}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"memU retrieve hook log failed: {exc}", file=sys.stderr)
    if trace["status"] == "failed":
        print("memU retrieve hook failed; see local retrieve logs", file=sys.stderr)
    if output is not None:
        if args.rewake:
            print(output["hookSpecificOutput"]["additionalContext"], file=sys.stderr)
            return 2
        print(json.dumps(output, ensure_ascii=False))
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("prompt-hook", help="Retrieve bounded context for a Claude UserPromptSubmit event on stdin")
    parser.add_argument("--base-dir", default=None, help="Host state directory for hook logs")
    parser.add_argument("--rewake", action="store_true", help="Wake Claude with retrieved context via asyncRewake")
    parser.set_defaults(handler=_cmd_prompt_hook)
