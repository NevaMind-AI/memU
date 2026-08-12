"""``memu-cola`` — memU's Cola host adapter."""

from __future__ import annotations

import sys

from memu.hosts.cola.sessions import SESSION_DIR, ColaTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "cola"

MEMORY_MD = "~/.cola/memory-bank/MEMORY.md"
"""Cola's durable memory-bank index, loaded as standing agent context."""

SKILLS_DIR = "~/.cola/resources/skills"
"""Cola's user-visible Agent Skills directory."""

SPEC = HostSpec(
    host=HOST,
    display="Cola",
    package="memu.hosts.cola",
    source_factory=ColaTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="Cola JSONL session directory (one directory per session scope)",
    instruction_path=MEMORY_MD,
    skills_dir=SKILLS_DIR,
    schedule_backend="native",
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
