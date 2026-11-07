"""``memu-pi`` — memU's pi host adapter."""

from __future__ import annotations

import sys
from typing import Any

from memu.hosts import hooks
from memu.hosts.host_cli import HostSpec, run
from memu.hosts.pi import hook_install, install, memorize_hook
from memu.hosts.pi.sessions import AGENT_DIR, SESSION_DIR, PiTranscriptSource

HOST = "pi"
AGENTS_MD = f"{AGENT_DIR}/AGENTS.md"
SKILLS_DIR = f"{AGENT_DIR}/skills"


def _register_extra(sub: Any) -> None:
    install.register(sub)
    hook_install.register(sub)


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
    hook=hooks.HookSpec(
        agent=hooks.HeadlessAgent(
            argv=(
                "pi",
                "-p",
                "--no-session",
                "--offline",
                "--no-extensions",
                "--no-skills",
                "--no-prompt-templates",
                "--no-context-files",
            )
        ),
        stream_output=memorize_hook.stream_agent,
    ),
    register_extra=_register_extra,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
