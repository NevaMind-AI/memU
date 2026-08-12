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

SESSION_ID_ENV = "CLAUDE_CODE_SESSION_ID"
"""Claude Code exports the running session's id to every tool subprocess, headless
``claude -p`` runs included — verified on 2.1.220. Its value is the transcript's
file name (``<projects>/<escaped cwd>/<sessionId>.jsonl``), which is exactly what
:meth:`TranscriptSource.session_id` reads back, so the bridging run can recognise
its own session without matching any content (#606)."""

SPEC = HostSpec(
    host=HOST,
    display="Claude Code",
    package="memu.hosts.claude_code",
    source_factory=ClaudeCodeTranscriptSource,
    session_dir=SESSION_DIR,
    session_help="Claude Code session log (one project dir per escaped cwd)",
    instruction_path=CLAUDE_MD,
    skills_dir=SKILLS_DIR,
    platform_task_docs=True,
    schedule_command="claude -p {prompt}",
    session_id_env=SESSION_ID_ENV,
    needs_headless_auth=True,
    install_hint=(
        "  Install a standalone claude:\n"
        "    winget install Anthropic.ClaudeCode\n"
        "    # or:  irm https://claude.ai/install.ps1 | iex\n"
        "    # or:  npm install -g @anthropic-ai/claude-code"
    ),
    auth_hint=(
        "    claude setup-token   # writes a token into your profile the task can read\n"
        "  or a persistent ANTHROPIC_API_KEY (`setx`, not a session-only `$env:`),"
    ),
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
