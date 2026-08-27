"""Command-line interface for memU.

A thin wrapper over the configured agentic memory backend exposing
``retrieve`` (progressive, LLM-free), ``list-files``, and ``commit``. Local
mode persists state through a SQLite database (``--db``, default
``./data/memu.sqlite3``); cloud mode forwards the same operations to the memU
v4 API.

Configuration mirrors the library defaults; every flag also reads a ``MEMU_*``
environment variable so CI/agents can configure once and pass only the command.

Usage:
    memu retrieve "What are this user's launch preferences?"
    memu list-files
    memu commit results.json
    memu memorize prepare session.json
    memu memorize commit
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import shlex
import sys
import time
from collections.abc import Callable, Coroutine
from typing import Any

from memu import events
from memu.agentic_backend import AgenticMemoryBackend
from memu.app.memorize.input import MemorizeInput
from memu.app.memorize.lifecycle import MemorizeWorkspace, commit_memorize, prepare_memorize
from memu.env import build_agentic_memory_backend_from_env, embedding_provider, env
from memu.hosts.bridging.resources import verify_resource_log

MEMORIZE_WORKSPACE = "~/.memu/developer"


def _env(name: str, default: str) -> str:
    # Falls through to ~/.memu/config.env before the default, so the CLI and the
    # host adapters resolve the same store — see memu.env.
    return env(name, default) or default


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("local service options (env var in parens; ignored in cloud mode)")
    group.add_argument(
        "--provider",
        default=embedding_provider(),
        help="Embedding provider id, e.g. openai, jina, voyage (MEMU_EMBED_PROVIDER)",
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


def _build_backend(args: argparse.Namespace) -> AgenticMemoryBackend:
    profile: dict[str, Any] = {"provider": args.provider}
    if args.embed_model:
        profile["embed_model"] = args.embed_model
    if args.base_url:
        profile["base_url"] = args.base_url
    if args.api_key:
        profile["api_key"] = args.api_key
    return build_agentic_memory_backend_from_env(
        local_embedding_profile=profile,
        local_database=args.db,
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


async def _cmd_retrieve(args: argparse.Namespace) -> int:
    backend = _build_backend(args)
    result = await backend.progressive_retrieve(args.query)
    _print_json(result)
    return 0


async def _cmd_list_files(args: argparse.Namespace) -> int:
    backend = _build_backend(args)
    # "list-files" shows everything, so follow next_cursor across pages (ADR 0014)
    # and gather the full set before printing.
    #
    # The same `memory_list` action the bridging store mirror records (ADR 0016),
    # with two things it cannot carry. This is the core `memu` binary, which has no
    # host at all, so `agent_platform` is `none` and there is no session — both
    # already the defined answer for this binary, not a gap. And nothing on this
    # path flushes: a hand-run command must not block on a POST, and unlike the
    # bridging pair this one has no reason to be the last thing that ever runs, so
    # the event waits in the spool for whichever run drains it next.
    files: list[dict[str, Any]] = []
    cursor: str | None = None
    started = time.monotonic()
    try:
        while True:
            result = await backend.list_all_recall_files(cursor=cursor)
            files.extend(result.get("recall_files", []))
            cursor = result.get("next_cursor")
            if not cursor:
                break
    except Exception:
        events.record_list(started=started, listed=len(files), success=False)
        raise
    events.record_list(started=started, listed=len(files), success=True)

    if args.json:
        _print_json({"recall_files": files})
        return 0
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
    backend = _build_backend(args)
    result = await backend.commit_results(
        recall_files=payload.get("recall_files"),
        resource=payload.get("resource"),
        user=payload.get("user"),
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


def _memorize_workspace(args: argparse.Namespace) -> MemorizeWorkspace:
    return MemorizeWorkspace(pathlib.Path(args.workspace).expanduser())


def _memorize_commit_command(args: argparse.Namespace, workspace: MemorizeWorkspace) -> str:
    command = "memu memorize commit"
    if args.workspace != MEMORIZE_WORKSPACE:
        command += f" --workspace {shlex.quote(str(workspace.base))}"
    return command


def _read_memorize_input(payload: str) -> MemorizeInput:
    if payload == "-":
        data = json.load(sys.stdin)
    else:
        path = pathlib.Path(payload).expanduser()
        if not path.exists():
            msg = f"no such file: {path}"
            raise FileNotFoundError(msg)
        data = json.loads(path.read_text(encoding="utf-8"))
    return MemorizeInput.model_validate(data)


async def _cmd_memorize_prepare(args: argparse.Namespace) -> int:
    if args.payload != "-":
        path = pathlib.Path(args.payload).expanduser()
        if not path.exists():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
    memorize_input = _read_memorize_input(args.payload)
    workspace = _memorize_workspace(args)
    verify_command = f"memu memorize verify-resources --workspace {shlex.quote(str(workspace.base))}"
    prepared = await prepare_memorize(
        memorize_input,
        workspace,
        _build_backend(args),
        verify_command=verify_command,
    )

    if args.json:
        _print_json({
            "workspace": str(workspace.base),
            "transcript": {
                "memory_path": str(prepared.transcript.memory_path),
                "skill_path": str(prepared.transcript.skill_path),
            },
            "jobs": [str(path) for path in prepared.jobs],
            "next_command": _memorize_commit_command(args, workspace),
        })
        return 0

    print("prepared developer session")
    print(f"  {len(prepared.jobs)} job(s)")
    print(f"  workspace: {workspace.base}")
    print("process the jobs in numeric order, then run:")
    print(f"  {_memorize_commit_command(args, workspace)}")
    return 0


async def _cmd_memorize_commit(args: argparse.Namespace) -> int:
    result = await commit_memorize(_memorize_workspace(args), _build_backend(args))
    if args.json:
        _print_json(result)
        return 0

    recall_files = result.get("recall_files", [])
    resources = result.get("resources", [])
    print(f"committed {len(recall_files)} recall file(s) and {len(resources)} resource(s)")
    for recall_file in recall_files:
        print(f"  - {recall_file.get('track')}/{recall_file.get('name')}")
    return 0


async def _cmd_memorize_verify_resources(args: argparse.Namespace) -> int:
    workspace = _memorize_workspace(args)
    kept = verify_resource_log(workspace.resource_log, workspace.resources)
    print(f"verified {kept} resource(s)")
    return 0


def _add_memorize_workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        default=MEMORIZE_WORKSPACE,
        help=f"Developer self-evolve workspace (default: {MEMORIZE_WORKSPACE})",
    )


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

    memorize = sub.add_parser(
        "memorize",
        help="Turn developer-supplied conversations into external self-evolve jobs",
    )
    memorize_actions = memorize.add_subparsers(dest="memorize_action", required=True)

    p = memorize_actions.add_parser("prepare", help="Prepare self-evolve jobs from a conversation batch")
    p.add_argument("payload", help='MemorizeInput JSON file, or "-" for stdin')
    _add_memorize_workspace(p)
    _add_common_options(p)
    p.set_defaults(handler=_cmd_memorize_prepare)

    p = memorize_actions.add_parser("commit", help="Commit the active self-evolve run")
    _add_memorize_workspace(p)
    _add_common_options(p)
    p.set_defaults(handler=_cmd_memorize_commit)

    p = memorize_actions.add_parser(
        "verify-resources",
        help="Internal: verify files logged by generated skill jobs",
    )
    _add_memorize_workspace(p)
    p.set_defaults(handler=_cmd_memorize_verify_resources)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Piped stdio on Windows falls back to the ANSI code page (gbk, cp1252, …),
    # which cannot encode retrieved memory content printed raw (ensure_ascii=False)
    # — and agents read every command through a pipe. Force UTF-8; on UTF-8 stdio
    # it's a no-op.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
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
