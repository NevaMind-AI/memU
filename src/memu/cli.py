"""Command-line interface for memU.

A thin wrapper over :class:`memu.app.MemoryService` exposing the agentic
surface: ``retrieve`` (progressive, LLM-free), ``list-files``, and ``commit``.
State persists across invocations through a SQLite database (``--db``, default
``./data/memu.sqlite3``), so the CLI composes like the library: commit in one
call, retrieve in the next.

Configuration mirrors the library defaults; every flag also reads a ``MEMU_*``
environment variable so CI/agents can configure once and pass only the command.

Usage:
    memu retrieve "What are this user's launch preferences?"
    memu list-files
    memu commit results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sys
from collections.abc import Callable, Coroutine
from typing import Any

from memu.env import database_config, env


def _env(name: str, default: str) -> str:
    # Falls through to ~/.memu/config.env before the default, so the CLI and the
    # host adapters resolve the same store — see memu.env.
    return env(name, default) or default


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("service options (env var in parens)")
    group.add_argument(
        "--provider",
        default=_env("MEMU_LLM_PROVIDER", "openai"),
        help="Embedding provider id, e.g. openai, jina, voyage (MEMU_LLM_PROVIDER)",
    )
    group.add_argument(
        "--embed-model",
        default=env("MEMU_EMBED_MODEL"),
        help="Embedding model override; defaults to the provider's default (MEMU_EMBED_MODEL)",
    )
    group.add_argument(
        "--base-url",
        default=env("MEMU_BASE_URL"),
        help="API base URL override (MEMU_BASE_URL)",
    )
    group.add_argument(
        "--api-key",
        default=env("MEMU_API_KEY"),
        help="API key value or env-var name; defaults to the provider's env var, e.g. OPENAI_API_KEY (MEMU_API_KEY)",
    )
    group.add_argument(
        "--db",
        default=_env("MEMU_DB", "./data/memu.sqlite3"),
        help="SQLite file path, postgres:// DSN, or ':memory:' (MEMU_DB)",
    )
    parser.add_argument("--json", action="store_true", help="Print the raw JSON response")


def _build_service(args: argparse.Namespace) -> Any:
    # Imported lazily so `memu --help` stays fast and dependency errors surface
    # only when a command actually runs.
    from memu.app import MemoryService

    profile: dict[str, Any] = {"provider": args.provider}
    if args.embed_model:
        profile["embed_model"] = args.embed_model
    if args.base_url:
        profile["base_url"] = args.base_url
    if args.api_key:
        profile["api_key"] = args.api_key
    return MemoryService(
        embedding_profiles={"default": profile},
        database_config=database_config(args.db),
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


async def _cmd_retrieve(args: argparse.Namespace) -> int:
    service = _build_service(args)
    result = await service.progressive_retrieve(args.query)
    _print_json(result)
    return 0


async def _cmd_list_files(args: argparse.Namespace) -> int:
    service = _build_service(args)
    result = await service.list_all_recall_files()
    if args.json:
        _print_json(result)
        return 0
    files = result.get("categories", [])
    print(f"{len(files)} recall file(s)")
    for f in files:
        print(f"  - {f.get('track')}/{f.get('name')}: {f.get('description') or ''}")
    return 0


async def _cmd_commit(args: argparse.Namespace) -> int:
    if args.payload == "-":
        payload = json.load(sys.stdin)
    else:
        path = pathlib.Path(args.payload).expanduser()
        if not path.exists():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
        payload = json.loads(path.read_text(encoding="utf-8"))
    service = _build_service(args)
    result = await service.commit_results(
        recall_files=payload.get("recall_files"),
        resource=payload.get("resource"),
    )
    if args.json:
        _print_json(result)
        return 0
    recall_files = result.get("recall_files", [])
    resources = result.get("resources", [])
    print(f"committed {len(recall_files)} recall file(s) and {len(resources)} resource(s)")
    for f in recall_files:
        print(f"  - {f.get('track')}/{f.get('name')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu",
        description="memU — personal memory as files. Commit prepared memory, retrieve context.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "retrieve",
        aliases=["search"],
        help="Single-shot embedding retrieval over segments/files/resources (LLM-free, fast)",
    )
    p.add_argument("query", help="Natural-language query")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_retrieve)

    p = sub.add_parser("list-files", help="List every recall file across the memory and skill tracks")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_list_files)

    p = sub.add_parser(
        "commit",
        help="Persist externally-prepared recall files and resources from a JSON payload",
    )
    p.add_argument(
        "payload",
        help='JSON file (or "-" for stdin) shaped {"recall_files": [...], "resource": [...]}',
    )
    _add_common_options(p)
    p.set_defaults(handler=_cmd_commit)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler: Callable[[argparse.Namespace], Coroutine[Any, Any, int]] = args.handler
    try:
        return asyncio.run(handler(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        if os.environ.get("MEMU_DEBUG") == "1":
            raise
        print(f"error: {exc} (set MEMU_DEBUG=1 for a traceback)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
