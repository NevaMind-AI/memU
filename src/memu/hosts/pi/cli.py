"""``memu-pi`` — memU's pi host adapter."""

from __future__ import annotations

import sys

from memu.hosts.host_cli import HostSpec, run
from memu.hosts.pi.sessions import AGENT_DIR, SESSION_DIR, PiTranscriptSource

HOST = "pi"
AGENTS_MD = f"{AGENT_DIR}/AGENTS.md"
SKILLS_DIR = f"{AGENT_DIR}/skills"

SPEC = HostSpec(
    host=HOST,
    display="pi",
    package="memu.hosts.pi",
    task_name="memu-bridging-pi",
    source_factory=PiTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="pi v3 JSONL session directory (one directory per encoded cwd)",
    instruction_path=AGENTS_MD,
    skills_dir=SKILLS_DIR,
    schedule_backend="os",
    schedule_command="pi -p {prompt}",
    session_id_env="PI_SESSION_ID",
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
