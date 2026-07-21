"""``memu-claude-code`` — the Claude Code host adapter's command-line surface.

The verbs are the shared host-adapter surface (:mod:`memu.hosts.host_cli`); this
module is the Claude Code declaration: where its sessions live, and which file
its standing instruction lands in.

Usage:
    memu-claude-code retrieve "<query>"    # the inject seam — what the agent runs each turn
    memu-claude-code install-instruction   # the inject seam — patch ~/.claude/CLAUDE.md to run it
    memu-claude-code prepare               # slice new sessions into job files
    memu-claude-code verify-resources      # filter the touched-file log (run by a job)
    memu-claude-code commit                # submit what the agent produced back to memU
    memu-claude-code doctor                # check config + store before relying on them
    memu-claude-code docs install          # print the agent-facing install guide
    memu-claude-code docs uninstall        # print the agent-facing removal guide
"""

from __future__ import annotations

import sys

from memu.hosts.claude_code.sessions import SESSION_DIR, ClaudeCodeTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "claude-code"

CLAUDE_MD = "~/.claude/CLAUDE.md"
"""Claude Code's global memory file — loaded into every session across every
project, so the inject seam lands here. (Project-level CLAUDE.md files exist too,
but the instruction belongs at the level retrieval works at: the user.)"""

SKILLS_DIR = "~/.claude/skills"
"""Claude Code's personal skills directory. Because it exists, the CLAUDE.md block
is a pointer and the retrieval procedure itself is installed here as a skill."""

SPEC = HostSpec(
    host=HOST,
    display="Claude Code",
    package="memu.hosts.claude_code",
    source_factory=ClaudeCodeTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="Claude Code session log (one project dir per escaped cwd)",
    instruction_path=CLAUDE_MD,
    skills_dir=SKILLS_DIR,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
