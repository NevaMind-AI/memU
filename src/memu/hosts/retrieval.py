"""The inject seam — one retrieval call, shared by every host adapter.

ADR 0008 gives each host two seams. *Record* genuinely differs per host: each
writes its session log its own way, which is what
:class:`~memu.hosts.base.TranscriptSource` exists to absorb. *Inject* does not —
whatever a host's prompt hook looks like, the retrieval it triggers is the same
query against the same store. So it lives here once, and each host CLI registers
it under its own binary (``memu-codex retrieve``, and whatever comes next),
because that binary is what the host's hook can reliably invoke.

This wraps :meth:`AgenticMixin.progressive_retrieve` rather than
``retrieve_workspace``. Both are LLM-free, embed the query once, rank the same
three layers, and return the same shape; ``progressive_retrieve`` runs those
stages inline instead of through the workflow engine. Neither does intention
routing, sufficiency checks, or summarization — that is ``memu retrieve``, which
is LLM-routed and far too heavy to put on a per-turn hook.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from memu.env import build_service_from_env


async def retrieve(query: str, where: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retrieve against the configured store. Returns ``segments``/``files``/``resources``.

    Embeddings are already stripped from the hits, so the result is safe to print.
    """
    service = build_service_from_env()
    result: dict[str, Any] = await service.progressive_retrieve(query, where=where)
    return result


async def _cmd_retrieve(args: argparse.Namespace) -> int:
    result = await retrieve(args.query)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


def register(sub: Any) -> None:
    """Add the ``retrieve`` subcommand to a host CLI's subparsers."""
    parser = sub.add_parser(
        "retrieve",
        help="LLM-free single-shot retrieval over memory, skills, and resources (what the inject hook runs)",
    )
    parser.add_argument("query", help="Natural-language query")
    parser.set_defaults(handler=_cmd_retrieve)
