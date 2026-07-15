"""The Cursor host adapter — ``memu-cursor``.

Binds ADR 0008's two seams onto Cursor: *record* as a scheduled bridging task
over ``~/.cursor/projects/*/agent-transcripts`` (see :mod:`memu.hosts.bridging`),
*inject* as a standing instruction in the project's ``AGENTS.md`` that points the
agent at the ``memu-cursor retrieve`` command.
"""

from memu.hosts.cursor.sessions import CursorTranscriptSource

__all__ = ["CursorTranscriptSource"]
