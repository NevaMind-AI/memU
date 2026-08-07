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
    memu-cursor docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.cursor.sessions import SESSION_DIR, CursorTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "cursor"
SESSION_ID_ENV = "CURSOR_CONVERSATION_ID"

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
    # --trust: cursor-agent refuses to run headless in an untrusted directory
    # (field-verified: exit 1 with "Workspace Trust Required"). The flag rides in
    # the template so both the auth gate and the scheduled run carry it, and the
    # trust lands on the task's working tree (~/.memu/hosts/cursor), nowhere else.
    # Never --yolo — that is the blanket permission skip the guides reject.
    schedule_backend="os",
    schedule_command="cursor-agent --trust -p {prompt}",
    # Cursor Agent 2026.08.04 injects its current conversation id into shell
    # tools under this name. Cursor names the transcript directory and JSONL
    # file with that same id, so TranscriptSource.session_id()'s stem default
    # maps the two sides exactly.
    session_id_env=SESSION_ID_ENV,
    needs_headless_auth=True,
    install_hint=(
        "  Install the standalone Cursor Agent CLI:\n"
        "    irm 'https://cursor.com/install?win32=true' | iex\n"
        "    # macOS/Linux/WSL:  curl https://cursor.com/install -fsSL | bash\n"
        "  Then re-run from a NEW terminal - this shell's PATH may predate the install."
    ),
    auth_hint=(
        "    sign in to the Cursor IDE on this machine (the CLI reuses that account\n"
        "    session), or run `cursor-agent login` once. Note: custom-provider (BYOK)\n"
        "    models do not work in the CLI - runs bill the Cursor account's plan,"
    ),
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
