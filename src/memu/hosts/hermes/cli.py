"""``memu-hermes`` — the Hermes Agent host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the Hermes declaration: where its session store lives (a SQLite
database, not a transcript directory), and which file its standing instruction
lands in.

Usage:
    memu-hermes retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-hermes install-instruction   # the inject seam — write the retrieve instruction into SOUL.md
    memu-hermes prepare               # slice new sessions into job files
    memu-hermes verify-resources      # filter the touched-file log (run by a job)
    memu-hermes commit                # submit what the agent produced back to memU
    memu-hermes doctor                # check config + store before relying on them
    memu-hermes docs install          # print the agent-facing install guide
    memu-hermes docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.hermes.sessions import HermesTranscriptSource, state_db_path
from memu.hosts.host_cli import HostSpec, run

HOST = "hermes"

SOUL_MD = "~/.hermes/SOUL.md"
"""Hermes's identity file — the one file loaded from ``HERMES_HOME`` into every
session regardless of working directory, so the inject seam lands here.
(Project-level ``.hermes.md``/``AGENTS.md`` files are per-directory and would
miss sessions started elsewhere.)"""

# No ``skills_dir``: Hermes is an *inline* host, not a skill host.
#
# Hermes has a ~/.hermes/skills directory, but skills there are pull-on-demand —
# the model only sees a skill's body after it calls ``skills_list`` then
# ``skill_view``, and only a relevance-selected subset of the installed skills is
# surfaced per turn. A "retrieve before every turn" skill is not reliably
# selected, so a SOUL.md *pointer* ("use the memu-retrieve skill") names a body
# the model never loads and the inject seam silently no-ops. (Observed: 0/8
# recall across a natural Session-B suite on Hermes; recall works the moment the
# skill is force-preloaded with ``-s memu-retrieve``.)
#
# Hosts that snapshot their skills into context at session start (OpenClaw) or
# always load their instruction file plus skill descriptions (Codex, Claude
# Code) can use the pointer shape. Hermes cannot, so it takes the full retrieval
# procedure inline in SOUL.md, which is present on every turn.

SPEC = HostSpec(
    host=HOST,
    display="Hermes",
    package="memu.hosts.hermes",
    source_factory=HermesTranscriptSource,
    session_dir=str(state_db_path()),
    session_help="Hermes SQLite session store (state.db under HERMES_HOME)",
    instruction_path=SOUL_MD,
    schedule_command="hermes -z {prompt}",
    schedule_prepare_session_dir=True,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
