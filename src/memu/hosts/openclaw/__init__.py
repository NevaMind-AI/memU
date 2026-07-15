"""The OpenClaw host adapter — ``memu-openclaw``.

Binds ADR 0008's two seams onto OpenClaw: *record* as a scheduled bridging task
over ``~/.openclaw/agents/*/sessions`` (see :mod:`memu.hosts.bridging`), *inject*
as a standing instruction in the workspace ``AGENTS.md`` that points the agent at
the ``memu-openclaw retrieve`` command.
"""

from memu.hosts.openclaw.sessions import OpenClawTranscriptSource

__all__ = ["OpenClawTranscriptSource"]
