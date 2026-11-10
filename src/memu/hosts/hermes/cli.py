"""``memu-hermes`` — the Hermes Agent host adapter's command-line surface.

The shared host-adapter verbs handle retrieval and session processing. Hermes
also exposes CLI-managed plugin installation and removal for automatic retrieval
and background memory.

Usage:
    memu-hermes install              # configure backend and enable memory hooks
    memu-hermes uninstall            # remove the managed plugin
    memu-hermes retrieve "<query>"    # retrieve memory manually
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
from typing import Any

from memu.hosts import hooks
from memu.hosts.hermes import hook, hook_install, install
from memu.hosts.hermes.sessions import HermesTranscriptSource, hermes_home, state_db_path
from memu.hosts.host_cli import HostSpec, run

HOST = "hermes"
SESSION_ID_ENV = "HERMES_SESSION_ID"

SOUL_MD = str(hermes_home() / "SOUL.md")
"""Hermes's identity file — the one file loaded from ``HERMES_HOME`` into every
session regardless of working directory, so the inject seam lands here.
(Project-level ``.hermes.md``/``AGENTS.md`` files are per-directory and would
miss sessions started elsewhere.)"""

# Retain the inline instruction commands for existing/manual installations.
# Hook installation manages the memu-memory plugin separately.


def _register_extra(sub: Any) -> None:
    # Legacy installs could include a retrieval skill even though new manual
    # instructions stay inline in SOUL.md.
    sub.choices["remove-instruction"].set_defaults(skills_dir=str(hermes_home() / "skills"))
    install.register(sub)
    hook_install.register(sub)


SPEC = HostSpec(
    host=HOST,
    display="Hermes",
    package="memu.hosts.hermes",
    task_name="memu-bridging-hermes",
    source_factory=HermesTranscriptSource,
    session_dir=str(state_db_path()),
    session_help="Hermes SQLite session store (state.db under HERMES_HOME)",
    instruction_path=SOUL_MD,
    schedule_backend="os",
    schedule_command="hermes -z {prompt}",
    schedule_prepare_session_dir=True,
    session_id_env=SESSION_ID_ENV,
    hook=hooks.HookSpec(
        agent=hooks.HeadlessAgent(argv=("hermes", "--ignore-rules")),
        stream_output=hook.stream_agent,
    ),
    register_extra=_register_extra,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
