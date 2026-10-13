"""``memu-dsh`` —— memU 的 DeepSeek Harness 宿主适配器。"""

from __future__ import annotations

import sys

from memu.hosts.dsh.sessions import TRANSCRIPTS_DIR, DshTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "dsh"
AGENTS_MD = "~/.dsh/AGENTS.md"
SKILLS_DIR = "~/.dsh/skills"

SPEC = HostSpec(
    host=HOST,
    display="DSH",
    package="memu.hosts.dsh",
    task_name="memu-bridging-dsh",
    source_factory=DshTranscriptSource,
    session_dir=TRANSCRIPTS_DIR,
    session_help="dsh-memu 插件导出的 DSH 会话转录目录 (每个 cwd 一个编码子目录)",
    instruction_path=AGENTS_MD,
    skills_dir=SKILLS_DIR,
    schedule_backend="external",
    session_id_env="DSH_SESSION_ID",
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
