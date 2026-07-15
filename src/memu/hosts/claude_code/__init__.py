"""The Claude Code host adapter — ``memu-claude-code``.

Binds ADR 0008's two seams onto Claude Code: *record* as a scheduled bridging
task over ``~/.claude/projects`` (see :mod:`memu.hosts.bridging`), *inject* as a
standing instruction in ``~/.claude/CLAUDE.md`` that points the agent at the
``memu-claude-code retrieve`` command.
"""

from memu.hosts.claude_code.sessions import ClaudeCodeTranscriptSource

__all__ = ["ClaudeCodeTranscriptSource"]
