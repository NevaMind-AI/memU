"""``memu-openclaw`` — the OpenClaw host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the OpenClaw declaration: where its session transcripts live, and which
file its standing instruction lands in.

Usage:
    memu-openclaw retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-openclaw install-instruction   # the inject seam — install the skill, point AGENTS.md at it
    memu-openclaw prepare               # slice new sessions into job files
    memu-openclaw verify-resources      # filter the touched-file log (run by a job)
    memu-openclaw commit                # submit what the agent produced back to memU
    memu-openclaw doctor                # check config + store before relying on them
    memu-openclaw docs install          # print the agent-facing install guide
    memu-openclaw docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.host_cli import HostSpec, run
from memu.hosts.openclaw.sessions import SESSION_DIR, OpenClawTranscriptSource

HOST = "openclaw"

AGENTS_MD = "~/.openclaw/workspace/AGENTS.md"
"""OpenClaw's workspace instruction file — loaded at the start of every session,
so the inject seam lands here. If the user runs a non-default workspace
(``OPENCLAW_WORKSPACE_DIR``, or a profile), pass ``--path``."""

SKILLS_DIR = "~/.openclaw/skills"
"""OpenClaw's managed skills directory (agentskills.io layout, snapshotted at
session start and loaded on demand). Because it exists, the AGENTS.md block is a
pointer and the retrieval procedure itself is installed here as a skill."""

SPEC = HostSpec(
    host=HOST,
    display="OpenClaw",
    package="memu.hosts.openclaw",
    source_factory=OpenClawTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="OpenClaw agents dir holding <agentId>/sessions transcripts",
    instruction_path=AGENTS_MD,
    skills_dir=SKILLS_DIR,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
