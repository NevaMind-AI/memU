"""``memu-hermes`` — the Hermes Agent host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the Hermes declaration: where its session store lives (a SQLite
database, not a transcript directory), and which file its standing instruction
lands in.

Usage:
    memu-hermes retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-hermes install-instruction   # the inject seam — install the skill, point SOUL.md at it
    memu-hermes prepare               # slice new sessions into job files
    memu-hermes verify-resources      # filter the touched-file log (run by a job)
    memu-hermes commit                # submit what the agent produced back to memU
    memu-hermes doctor                # check config + store before relying on them
    memu-hermes docs install          # print the agent-facing install guide
    memu-hermes docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.hermes.sessions import STATE_DB, HermesTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "hermes"

SOUL_MD = "~/.hermes/SOUL.md"
"""Hermes's identity file — the one file loaded from ``HERMES_HOME`` into every
session regardless of working directory, so the inject seam lands here.
(Project-level ``.hermes.md``/``AGENTS.md`` files are per-directory and would
miss sessions started elsewhere.)"""

SKILLS_DIR = "~/.hermes/skills"
"""Hermes's skills directory (agentskills.io layout, loaded on demand via
``skills_list``/``skill_view``). Because it exists, the SOUL.md block is a
pointer and the retrieval procedure itself is installed here as a skill."""

SPEC = HostSpec(
    host=HOST,
    display="Hermes",
    package="memu.hosts.hermes",
    source_factory=HermesTranscriptSource,
    session_dir=STATE_DB,
    session_help="Hermes SQLite session store (state.db under HERMES_HOME)",
    instruction_path=SOUL_MD,
    skills_dir=SKILLS_DIR,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
