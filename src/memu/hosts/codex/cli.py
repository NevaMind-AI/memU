"""``memu-codex`` — the Codex host adapter's command-line surface.

Its own binary, not a subcommand of ``memu``, and deliberately so: ``memu`` is
memU's algorithm surface, this is a *host adapter* (ADR 0008). Keeping them apart
means host plumbing never accretes onto the core CLI, and ``memu --help`` keeps
describing the library rather than a grab-bag.

Every command here is a stable ``PATH`` contract, which is the point: the
scheduled bridging task embeds these command strings in its recurring prompt, and
a command survives the reinstalls and directory moves that a baked-in
``<VENV_PYTHON> /abs/path/to/script.py`` pair does not (ADR 0009).

The verbs themselves are shared across every host adapter and live in
:mod:`memu.hosts.host_cli`; this module is the Codex declaration.

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
import sys

from memu.hosts.codex.sessions import SESSION_DIR, CodexTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "codex"

VERIFY_COMMAND = "memu-codex verify-resources"
"""What the resource job tells the agent to run. A command, never a path."""

AGENTS_MD = "~/.codex/AGENTS.md"
"""Codex's global instruction file — loaded into every session, so the inject seam
lands here. The path is the only part of that seam that is Codex-specific."""

SPEC = HostSpec(
    host=HOST,
    display="Codex",
    package="memu.hosts.codex",
    source_factory=CodexTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="Codex session log",
    instruction_path=AGENTS_MD,
    # Codex shipped before per-host working trees; its ~/.memu layout is a
    # compatibility contract with already-scheduled bridging prompts (ADR 0010).
    base_dir="~/.memu",
)


def build_parser() -> argparse.ArgumentParser:
    from memu.hosts.host_cli import build_parser as _build

    return _build(SPEC)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
