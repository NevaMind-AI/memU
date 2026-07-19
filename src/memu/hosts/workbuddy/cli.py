"""``memu-workbuddy`` — the WorkBuddy host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the WorkBuddy declaration: where its sessions live, and which file its
standing instruction lands in.

Usage:
    memu-workbuddy retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-workbuddy install-instruction   # the inject seam — patch ~/.workbuddy/MEMORY.md
    memu-workbuddy prepare               # slice new sessions into job files
    memu-workbuddy verify-resources      # filter the touched-file log (run by a job)
    memu-workbuddy commit                # submit what the agent produced back to memU
    memu-workbuddy doctor                # check config + store before relying on them
    memu-workbuddy docs install          # print the agent-facing install guide
    memu-workbuddy docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.workbuddy.sessions import SESSION_DIR, WorkBuddyTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "workbuddy"

MEMORY_MD = "~/.workbuddy/MEMORY.md"
"""WorkBuddy's global memory file — loaded into every session, so the inject
seam lands here.  (User-level: ``~/.workbuddy/MEMORY.md``; per-project memory
files also exist but the instruction belongs at the level retrieval works at.)"""

SPEC = HostSpec(
    host=HOST,
    display="WorkBuddy",
    package="memu.hosts.workbuddy",
    source_factory=WorkBuddyTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="WorkBuddy session log (one project dir per escaped cwd)",
    instruction_path=MEMORY_MD,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
