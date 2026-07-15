"""Command-line interface for memU.

A thin wrapper over :class:`memu.app.MemoryService` exposing the four public
entry points (``memorize``, ``memorize-workspace``, ``retrieve``,
``retrieve-workspace``) plus the memory-file export. State persists across
invocations through a SQLite database (``--db``, default ``./data/memu.sqlite3``),
so the CLI composes like the library: memorize in one call, retrieve in the next.

Configuration mirrors the library defaults; every flag also reads a ``MEMU_*``
environment variable so CI/agents can configure once and pass only the command.

Usage:
    memu memorize notes/meeting.md
    memu memorize-workspace ./workspace
    memu retrieve "What are this user's launch preferences?"
    memu retrieve-workspace "deploy checklist"
    memu export
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

from memu.blob.folder import EXT_MODALITY, infer_modality
from memu.env import database_config, env

MODALITIES = ("conversation", "document", "image", "video", "audio")


def _env(name: str, default: str) -> str:
    # Falls through to ~/.memu/config.env before the default, so the CLI and the
    # host adapters resolve the same store — see memu.env.
    return env(name, default) or default


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("service options (env var in parens)")
    group.add_argument(
        "--provider",
        default=_env("MEMU_LLM_PROVIDER", "openai"),
        help="LLM provider id, e.g. openai, anthropic, deepseek (MEMU_LLM_PROVIDER)",
    )
    group.add_argument(
        "--model",
        default=env("MEMU_CHAT_MODEL"),
        help="Chat model override; defaults to the provider's default (MEMU_CHAT_MODEL)",
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
    group.add_argument(
        "--resources-dir",
        default=_env("MEMU_RESOURCES_DIR", "./data/resources"),
        help="Directory where ingested source files are copied (MEMU_RESOURCES_DIR)",
    )
    group.add_argument(
        "--memory-dir",
        default=_env("MEMU_MEMORY_DIR", "./data/memory"),
        help="Directory for the INDEX.md/MEMORY.md/SKILL.md markdown tree (MEMU_MEMORY_DIR)",
    )
    group.add_argument(
        "--synthesize",
        action="store_true",
        default=_env("MEMU_SYNTHESIZE", "") == "1",
        help="LLM-synthesize MEMORY.md/SKILL.md overviews instead of deterministic indexes (MEMU_SYNTHESIZE=1)",
    )
    parser.add_argument("--json", action="store_true", help="Print the raw JSON response")


def _build_service(args: argparse.Namespace, *, memory_files: bool) -> Any:
    # Imported lazily so `memu --help` stays fast and dependency errors surface
    # only when a command actually runs.
    from memu.app import MemoryService

    llm: dict[str, Any] = {"provider": args.provider}
    if args.model:
        llm["chat_model"] = args.model
    if args.base_url:
        llm["base_url"] = args.base_url
    if args.api_key:
        llm["api_key"] = args.api_key
    return MemoryService(
        llm_profiles={"default": llm},
        database_config=database_config(args.db),
        blob_config={"resources_dir": args.resources_dir},
        memory_files_config={
            "enabled": memory_files,
            "output_dir": args.memory_dir,
            "synthesize": args.synthesize,
        },
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


async def _cmd_memorize(args: argparse.Namespace) -> int:
    path = pathlib.Path(args.path).expanduser()
    if not path.exists():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    modality = args.modality or infer_modality(path)
    if modality is None:
        supported = ", ".join(sorted(EXT_MODALITY))
        print(
            f"error: cannot infer modality for '{path.suffix}'; pass --modality (supported extensions: {supported})",
            file=sys.stderr,
        )
        return 2
    service = _build_service(args, memory_files=False)
    result = await service.memorize(resource_url=str(path), modality=modality)
    if args.json:
        _print_json(result)
        return 0
    entries = result.get("items", [])
    files = result.get("categories", [])
    print(f"memorized {path} ({modality}): {len(entries)} entries across {len(files)} files")
    for f in files:
        print(f"  - {f.get('name')}")
    return 0


async def _cmd_memorize_workspace(args: argparse.Namespace) -> int:
    folder = pathlib.Path(args.folder).expanduser()
    if not folder.is_dir():
        print(f"error: no such folder: {folder}", file=sys.stderr)
        return 2
    service = _build_service(args, memory_files=not args.no_export)
    result = await service.memorize_workspace(folder=str(folder))
    if args.json:
        _print_json(result)
        return 0
    added, modified, deleted = result.get("added", []), result.get("modified", []), result.get("deleted", [])
    print(f"synced {folder}: +{len(added)} added, ~{len(modified)} modified, -{len(deleted)} deleted")
    for label, names in (("+", added), ("~", modified), ("-", deleted)):
        for name in names:
            print(f"  {label} {name}")
    if not args.no_export:
        print(f"memory files written to {args.memory_dir}")
    return 0


async def _cmd_retrieve(args: argparse.Namespace) -> int:
    service = _build_service(args, memory_files=False)
    result = await service.retrieve(queries=[{"role": "user", "content": {"text": args.query}}])
    _print_json(result)
    return 0


async def _cmd_retrieve_workspace(args: argparse.Namespace) -> int:
    service = _build_service(args, memory_files=False)
    result = await service.retrieve_workspace(args.query)
    _print_json(result)
    return 0


async def _cmd_export(args: argparse.Namespace) -> int:
    service = _build_service(args, memory_files=True)
    result = await service.export_memory_files()
    if args.json:
        _print_json(result)
    else:
        print(f"memory files written to {args.memory_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu",
        description="memU — personal memory as files. Memorize sources, retrieve context.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("memorize", help="Memorize a single file (conversation, document, image, audio, video)")
    p.add_argument("path", help="Path to the source file")
    p.add_argument("--modality", choices=MODALITIES, help="Override the extension-inferred modality")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_memorize)

    p = sub.add_parser(
        "memorize-workspace",
        aliases=["sync"],
        help="Diff-sync a folder into memory (chat/ -> memory, agent/ -> skills, other -> index)",
    )
    p.add_argument("folder", help="Workspace folder to scan and sync")
    p.add_argument("--no-export", action="store_true", help="Skip rebuilding the markdown memory tree")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_memorize_workspace)

    p = sub.add_parser("retrieve", help="LLM-routed retrieval over memorized entries (heavy, high quality)")
    p.add_argument("query", help="Natural-language query")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_retrieve)

    p = sub.add_parser(
        "retrieve-workspace",
        aliases=["search"],
        help="Single-shot embedding retrieval over segments/files/resources (LLM-free, fast)",
    )
    p.add_argument("query", help="Natural-language query")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_retrieve_workspace)

    p = sub.add_parser("export", help="Rebuild the INDEX.md/MEMORY.md/SKILL.md markdown tree from the store")
    _add_common_options(p)
    p.set_defaults(handler=_cmd_export)

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
