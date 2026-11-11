"""``memu-hermes`` — the Hermes Agent host adapter's command-line surface.

The shared host-adapter verbs handle retrieval and session processing. Hermes
installs on-demand retrieval in a managed SOUL.md block.

Usage:
    memu-hermes install              # configure backend and patch SOUL.md
    memu-hermes uninstall            # remove managed instructions and legacy plugin
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
from dataclasses import replace
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
    # Retain the old skill location only for migration/removal. New retrieval
    # instructions live entirely in the managed SOUL.md block.
    sub.choices["install-instruction"].description = "Install on-demand memU retrieval inline in SOUL.md"
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
    # Resolve the active profile at invocation, including embedded callers that
    # change HERMES_HOME after importing this module.
    spec = replace(SPEC, instruction_path=str(hermes_home() / "SOUL.md"), session_dir=str(state_db_path()))
    return run(spec, argv)


if __name__ == "__main__":
    sys.exit(main())
