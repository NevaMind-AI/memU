"""``memu-cursor`` — the Cursor host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the Cursor declaration: where its agent transcripts live, and which
file its standing instruction lands in.

Usage:
    memu-cursor retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-cursor install-instruction   # the inject seam — patch AGENTS.md to run it
    memu-cursor prepare               # slice new sessions into job files
    memu-cursor verify-resources      # filter the touched-file log (run by a job)
    memu-cursor commit                # submit what the agent produced back to memU
    memu-cursor doctor                # check config + store before relying on them
    memu-cursor docs install          # print the agent-facing install guide
"""

from __future__ import annotations

import sys

from memu.hosts.cursor.sessions import SESSION_DIR, CursorTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "cursor"

AGENTS_MD = "./AGENTS.md"
"""Cursor has no global user-level instruction *file* (User Rules are IDE
settings, out of a CLI's reach) — its Agent reads ``AGENTS.md`` from the project
root. So the inject seam is per project: run ``install-instruction`` inside each
project that should retrieve from memU, or pass ``--path``."""

SPEC = HostSpec(
    host=HOST,
    display="Cursor",
    package="memu.hosts.cursor",
    source_factory=CursorTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="Cursor agent-transcript root (one project dir per escaped cwd)",
    instruction_path=AGENTS_MD,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
