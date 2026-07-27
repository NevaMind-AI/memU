"""``memu-workbuddy`` — the WorkBuddy host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the WorkBuddy declaration: where its sessions live, and which file its
standing instruction lands in.

Usage:
    memu-workbuddy retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-workbuddy install-instruction   # the inject seam — patch ~/.workbuddy/SOUL.md
    memu-workbuddy prepare               # slice new sessions into job files
    memu-workbuddy verify-resources      # filter the touched-file log (run by a job)
    memu-workbuddy commit                # submit what the agent produced back to memU
    memu-workbuddy doctor                # check config + store before relying on them
    memu-workbuddy docs install          # print the agent-facing install guide
    memu-workbuddy docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.host_cli import HostSpec, run
from memu.hosts.workbuddy.sessions import SESSION_DIR, WorkBuddyTranscriptSource

HOST = "workbuddy"

SOUL_MD = "~/.workbuddy/SOUL.md"
"""WorkBuddy's global behavior file — loaded into every session, so standing
instructions that must run before every answer belong here rather than among the
facts and summaries in long-term memory."""

MEMORY_MD = "~/.workbuddy/MEMORY.md"
"""The legacy inject target. Existing installs are migrated from this file when
``install-instruction`` runs against the default ``SOUL_MD`` target."""

INLINE_INSTRUCTION_PREAMBLE = """\
`memu-workbuddy` is a command-line executable on `PATH`, not a WorkBuddy tool
name. Use WorkBuddy's `bash` tool to execute the command below. Do not look for a
tool named `memu-workbuddy`.

If the `bash` tool is unavailable or the command fails, report that memU retrieval
is unavailable. Do not silently treat an execution failure as an empty retrieval
result.
"""

SPEC = HostSpec(
    host=HOST,
    display="WorkBuddy",
    package="memu.hosts.workbuddy",
    source_factory=WorkBuddyTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="WorkBuddy session log (one project dir per escaped cwd)",
    instruction_path=SOUL_MD,
    legacy_instruction_paths=(MEMORY_MD,),
    inline_instruction_preamble=INLINE_INSTRUCTION_PREAMBLE,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
