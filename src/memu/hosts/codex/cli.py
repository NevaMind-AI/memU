"""``memu-codex`` — the Codex host adapter's command-line surface.

Its own binary, not a subcommand of ``memu``, and deliberately so: ``memu`` is
memU's algorithm surface, this is a *host adapter* (ADR 0008). Keeping them apart
means host plumbing never accretes onto the core CLI, and ``memu --help`` keeps
describing the library rather than a grab-bag.

Every command here is a stable ``PATH`` contract, which is the point: the
scheduled bridging task embeds these command strings in its recurring prompt, and
a command survives the reinstalls and directory moves that a baked-in
``<VENV_PYTHON> /abs/path/to/script.py`` pair does not (ADR 0009).

Usage:
    memu-codex retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-codex install-instruction   # the inject seam — patch ~/.codex/AGENTS.md to run it
    memu-codex prepare               # slice new sessions into job files
    memu-codex verify-resources      # filter the touched-file log (run by a job)
    memu-codex commit                # submit what the agent produced back to memU
    memu-codex doctor                # check config + store before relying on them
    memu-codex docs install          # print the agent-facing install guide
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Callable, Coroutine
from importlib.resources import files
from typing import Any

from memu.hosts import instruction, retrieval
from memu.hosts.bridging import Layout, commit, prepare
from memu.hosts.bridging.pipeline import MAX_JOBS
from memu.hosts.bridging.resources import verify_resource_log
from memu.hosts.codex.sessions import SESSION_DIR, CodexTranscriptSource

HOST = "codex"

VERIFY_COMMAND = "memu-codex verify-resources"
"""What the resource job tells the agent to run. A command, never a path."""

AGENTS_MD = "~/.codex/AGENTS.md"
"""Codex's global instruction file — loaded into every session, so the inject seam
lands here. The path is the only part of that seam that is Codex-specific."""

DOCS = {"install": "INSTALL.md", "task": "BRIDGING_TASK.md"}


def _layout(args: argparse.Namespace) -> Layout:
    return Layout.default(host=HOST, base=args.base_dir)


async def _cmd_prepare(args: argparse.Namespace) -> int:
    source = CodexTranscriptSource(args.session_dir)
    if not source.root().is_dir():
        print(f"error: no Codex session log at {source.root()}", file=sys.stderr)
        return 2

    layout = _layout(args)
    num_sessions = await prepare(source, layout, verify_command=VERIFY_COMMAND, max_jobs=args.max_jobs)
    num_jobs = 2 * num_sessions + 1
    print(f"prepared {num_sessions} session(s) -> {num_jobs} job(s) in {layout.jobs}")
    if num_sessions == 0:
        print("no new session turns since the last run; nothing to mine")
    return 0


async def _cmd_commit(args: argparse.Namespace) -> int:
    result = await commit(_layout(args))
    recall_files = result.get("recall_files", [])
    resources = result.get("resources", [])
    if not recall_files and not resources:
        print("nothing to commit")
        return 0
    print(f"committed {len(recall_files)} recall file(s) and {len(resources)} resource(s)")
    for recall_file in recall_files:
        print(f"  - {recall_file.get('track')}/{recall_file.get('name')}")
    return 0


async def _cmd_verify_resources(args: argparse.Namespace) -> int:
    layout = _layout(args)
    kept = verify_resource_log(layout.resource_log, layout.resources)
    print(f"{kept} resource(s) written to {layout.resources}")
    return 0


async def _cmd_doctor(args: argparse.Namespace) -> int:
    """Prove config resolves and the store answers — the install guide's verify gate.

    Deliberately exercises the same call the inject hook will, so a green doctor
    means the hook's retrieval works, not merely that some store opened.
    """
    from memu.env import CONFIG_ENV, embedding_provider, env

    result = await retrieval.retrieve("smoke test")
    found = sum(len(result.get(layer, [])) for layer in ("segments", "files", "resources"))
    print(f"config    {os.path.expanduser(CONFIG_ENV)}")
    print(f"store     {env('MEMU_DB')}")
    print(f"provider  {embedding_provider()}")
    print(f"retrieval ok ({found} hit(s) for a smoke-test query; 0 is fine on a new store)")
    return 0


async def _cmd_docs(args: argparse.Namespace) -> int:
    print((files("memu.hosts.codex") / DOCS[args.doc]).read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-codex",
        description="memU's Codex host adapter — the scheduled bridging task and its install guide.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def with_base(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--base-dir", default="~/.memu", help="memU working directory (default: ~/.memu)")
        return p

    # Both halves of the inject seam: what the agent runs, and what tells it to.
    # Shared across hosts, so they are registered, not redefined — only the file
    # the instruction lands in is ours to name.
    retrieval.register(sub)
    instruction.register(sub, path=AGENTS_MD)

    p = with_base(sub.add_parser("prepare", help="Slice new Codex sessions into self-evolve job files"))
    p.add_argument("--session-dir", default=SESSION_DIR, help=f"Codex session log (default: {SESSION_DIR})")
    p.add_argument("--max-jobs", type=int, default=MAX_JOBS, help=f"Sessions per run (default: {MAX_JOBS})")
    p.set_defaults(handler=_cmd_prepare)

    p = with_base(sub.add_parser("commit", help="Submit what the self-evolve jobs produced back into memU"))
    p.set_defaults(handler=_cmd_commit)

    p = with_base(
        sub.add_parser("verify-resources", help="Filter the touched-file log into the describe-me resource file")
    )
    p.set_defaults(handler=_cmd_verify_resources)

    p = sub.add_parser("doctor", help="Verify MEMU_* config resolves and the store is reachable")
    p.set_defaults(handler=_cmd_doctor)

    p = sub.add_parser("docs", help="Print a packaged agent-facing guide")
    p.add_argument("doc", choices=sorted(DOCS), help="install: the setup guide; task: the bridging-task procedure")
    p.set_defaults(handler=_cmd_docs)

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
