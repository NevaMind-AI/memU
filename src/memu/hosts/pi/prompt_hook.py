"""pi submit retrieval, invoked by the packaged extension without blocking input."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from memu.env import LONG_QUERY_CHARS
from memu.hosts.pi.query_extraction import select_query
from memu.hosts.retrieval import QueryKind, render_context, retrieve


async def prompt_hook(args: argparse.Namespace) -> int:
    started = time.monotonic()
    trace: dict[str, Any] = {"observed_at": datetime.now(UTC).isoformat(), "status": "started"}
    context = None
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or not isinstance(event.get("prompt"), str):
            raise TypeError("Expected a prompt object")  # noqa: TRY003, TRY301
        prompt = event["prompt"]
        trace.update(session_id=event.get("session_id"), source=event.get("source"))
        if event.get("source") == "extension" or not prompt.strip():
            trace["status"] = "input_skipped"
        else:
            for name in ("provider", "model"):
                if event.get(name) is not None and not isinstance(event[name], str):
                    raise TypeError(f"Expected {name} to be a string")  # noqa: TRY003, TRY301
            query = await asyncio.to_thread(
                select_query, prompt, trace, provider=event.get("provider"), model=event.get("model")
            )
            kind: QueryKind = (
                "extracted"
                if trace.get("query_source") == "extracted"
                else "long"
                if sum(not char.isspace() for char in prompt) >= LONG_QUERY_CHARS
                else "short"
            )
            trace.update(
                query=query,
                query_kind=kind,
                query_truncated=trace.get("query_source") == "prefix",
                prompt_chars=len(prompt),
                query_chars=len(query),
                prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            )
            remaining = max(0.001, 40 - (time.monotonic() - started))
            memories = await asyncio.wait_for(retrieve(query, query_kind=kind), timeout=remaining)
            context = render_context(memories)
            counts = {layer: len(memories.get(layer, [])) for layer in ("hits", "resources")}
            trace.update(
                status="context_returned" if any(counts.values()) else "empty_result",
                retrieve_result=memories,
                additional_context=context,
                counts=counts,
                returned_counts=counts,
                omitted_counts=dict.fromkeys(counts, 0),
            )
    except Exception as exc:
        trace.update(status="failed", error=str(exc), error_type=type(exc).__name__)
    trace["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    try:
        directory = Path(args.base_dir).expanduser() / "log/hooks/retrieve"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{uuid4()}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"memU retrieval log failed: {exc}", file=sys.stderr)
    print(json.dumps({"context": context}, ensure_ascii=False))
    if trace["status"] == "failed":
        print(f"{trace['error_type']}: {trace['error']}", file=sys.stderr)
        return 1
    return 0
