"""The inject seam — one retrieval call, shared by every host adapter.

ADR 0008 gives each host two seams. *Record* genuinely differs per host: each
writes its session log its own way, which is what
:class:`~memu.hosts.base.TranscriptSource` exists to absorb. *Inject* does not —
whatever a host's prompt hook looks like, the retrieval it triggers is the same
query against the same store. So it lives here once, and each host CLI registers
it under its own binary (``memu-codex retrieve``, and whatever comes next),
because that binary is what the host's hook can reliably invoke.

This wraps :meth:`AgenticMixin.progressive_retrieve`: LLM-free, the query is
embedded once, and the segment/file/resource layers come back ranked. No
intention routing, sufficiency checks, or summarization — cheap enough to run
on a per-turn hook.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from memu import events
from memu.env import LONG_QUERY_CHARS, QueryKind, build_agentic_memory_backend_from_env, retrieval_min_score
from memu.hosts.bridging.layout import BASE_DIR, TRACK_DIRS
from memu.hosts.bridging.recall_files import write_recall_file


async def retrieve(
    query: str, where: dict[str, Any] | None = None, *, query_kind: QueryKind | None = None
) -> dict[str, Any]:
    """Retrieve against the configured backend. Returns self-contained ``hits`` and ``resources``.

    Embeddings are already stripped from the hits, so the result is safe to print.
    :func:`_shape_for_agent` then reshapes the raw store records into the
    self-contained form the standing instruction promises (see
    :mod:`memu.hosts.instruction`).
    """
    kind = query_kind or ("long" if sum(not c.isspace() for c in query) >= LONG_QUERY_CHARS else "short")
    min_score = retrieval_min_score(kind)
    backend = build_agentic_memory_backend_from_env()
    result: dict[str, Any] = await backend.progressive_retrieve(query, where=where)
    segment_count = len(result.get("segments", []))
    if min_score is not None:
        result["segments"] = [s for s in result.get("segments", []) if s["score"] >= min_score]
        file_ids = {s["recall_file_id"] for s in result["segments"]}
        result["files"] = [f for f in result.get("files", []) if f["id"] in file_ids]
    shaped = _shape_for_agent(result)
    shaped["retrieval_status"] = {
        "status": "succeeded",
        "query_kind": kind,
        "min_score": min_score,
        "candidate_segments": segment_count,
        "filtered_segments": segment_count - len(result.get("segments", [])),
        "retained_segments": len(result.get("segments", [])),
        "returned_hits": len(shaped["hits"]),
    }
    return shaped


def _shape_for_agent(result: dict[str, Any]) -> dict[str, Any]:
    """Join matched text with source details so each hit is self-contained.

    Scores describe the matched segment; timestamps describe its source file.
    Return at most five hits in ranked order to bound per-turn context overhead.
    Files without matched segments remain source-only hits. Missing sources do
    not discard matched text. Mirrorable sources provide a path; others retain
    their content inline. Database IDs and scope fields stay internal.
    """
    base = Path(os.path.expanduser(BASE_DIR))
    sources: dict[str, dict[str, Any]] = {}
    files = result.get("files", [])
    for file in files:
        source = {key: file[key] for key in ("description", "track", "created_at", "updated_at") if key in file}
        subdir = TRACK_DIRS.get(file.get("track") or "")
        if subdir is not None and file.get("name"):
            source["path"] = str(write_recall_file(base, subdir, file))
        elif "content" in file:
            source["content"] = file["content"]
        sources[file["id"]] = source

    hits = []
    matched_files = set()
    for segment in result.get("segments", []):
        file_id = segment.get("recall_file_id")
        hit = {key: segment[key] for key in ("text", "track", "score") if key in segment}
        hit.update(sources.get(file_id, {}))
        hits.append(hit)
        matched_files.add(file_id)

    for file in files:
        if file["id"] not in matched_files:
            hit = dict(sources[file["id"]])
            if "score" in file:
                hit["score"] = file["score"]
            hits.append(hit)

    resources = []
    for resource in result.get("resources", []):
        item = {key: resource[key] for key in ("caption", "score", "created_at", "updated_at") if key in resource}
        path = resource.get("url", resource.get("local_path"))
        if path is not None:
            item["path"] = path
        resources.append(item)
    return {"hits": hits[:5], "resources": resources}


async def _cmd_retrieve(args: argparse.Namespace) -> int:
    # Delivered inline on both legs, never flushed (ADR 0016): the backend wants the
    # retrieval event promptly and accepted the round trip that costs, but this is
    # still the per-turn hook, so what either leg may spend is *one* POST —
    # `deliver=True` sends that envelope alone and spools it if it does not land.
    # `events.flush()` here would drain the whole spool, up to 200 serial requests on
    # the hottest path in the product, and that bound is what may never be relaxed.
    # The query text is deliberately not among what is recorded — counts only.
    query = args.query
    if args.query_stdin:
        reconfigure = getattr(sys.stdin, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", newline="")
        query = sys.stdin.read()
    started = time.monotonic()
    try:
        result = await retrieve(query, query_kind=args.query_kind) if args.query_kind else await retrieve(query)
    except Exception:
        # `memory_search_failed`, and only ever for an exception this command
        # actually raised. An agent reporting `--stage retrieve` — retrieval quietly
        # returning nothing for a week — is a different proposition with a different
        # provenance, and stays on `agent_error_reported` (ADR 0016 §4).
        #
        # Delivered, like the success leg. A store this hook cannot reach breaks the
        # bridging pair with it, so the later flush this event would otherwise wait
        # for is the same machinery its own failure implicates — leaving it spooled
        # makes a broken machine the one that reports least. The cost is the same
        # constant either leg pays, one POST, and it is bounded by `_TIMEOUT_SECONDS`
        # rather than by how far behind the spool has fallen. What does not follow is
        # a flush: `host_cli.run` still exempts `retrieve` from the error handler's,
        # because *that* is the unbounded one.
        events.record_outcome(
            events.MEMORY_SEARCH_SUCCEEDED,
            events.MEMORY_SEARCH_FAILED,
            host=args.host,
            session_id_env=args.session_id_env,
            success=False,
            deliver=True,
            result_count=0,
            latency_ms=round((time.monotonic() - started) * 1000),
        )
        raise
    # Read before printing, so `latency_ms` stays what it means everywhere else —
    # the retrieval itself — rather than growing to include serialising the result
    # and the reporting POST that now follows it.
    latency_ms = round((time.monotonic() - started) * 1000)
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=False, default=str))
    # Recorded after the result is on stdout, never before: this is the one part of
    # the command that blocks on the network, and the agent's answer must not sit
    # behind it.
    events.record_outcome(
        events.MEMORY_SEARCH_SUCCEEDED,
        events.MEMORY_SEARCH_FAILED,
        host=args.host,
        session_id_env=args.session_id_env,
        success=True,
        deliver=True,
        result_count=events.counts(result, layers=("hits", "resources")),
        latency_ms=latency_ms,
    )
    return 0


def register(sub: Any, *, host: str = "", session_id_env: str = "") -> None:
    """Add the ``retrieve`` subcommand to a host CLI's subparsers.

    ``host`` and ``session_id_env`` come from the caller's :class:`HostSpec` and
    are carried on the parser defaults purely so the event this command records
    can name its platform and session — this module has no other access to them.
    """
    parser = sub.add_parser(
        "retrieve",
        help="LLM-free single-shot retrieval over memory, skills, and resources (what the inject hook runs)",
    )
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument("query", nargs="?", help="Natural-language query")
    query.add_argument("--query-stdin", action="store_true", help="Read the complete UTF-8 query from stdin")
    parser.add_argument(
        "--query-kind",
        choices=("short", "long", "extracted"),
        help="Score cutoff category; defaults to short/long by 200 non-whitespace characters",
    )
    parser.set_defaults(handler=_cmd_retrieve, host=host, session_id_env=session_id_env)
