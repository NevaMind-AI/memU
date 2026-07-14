"""The Codex host adapter — ``memu-codex``.

Binds ADR 0008's two seams onto Codex: *record* as a scheduled bridging task over
``~/.codex/sessions`` (see :mod:`memu.hosts.bridging`), *inject* as a
UserPromptSubmit hook that points the agent at the ``memu`` CLI.
"""

from memu.hosts.codex.sessions import CodexTranscriptSource

__all__ = ["CodexTranscriptSource"]
