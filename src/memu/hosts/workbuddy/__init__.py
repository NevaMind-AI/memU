"""The WorkBuddy host adapter — ``memu-workbuddy``.

Binds ADR 0008's two seams onto WorkBuddy: *record* as a scheduled bridging
task over ``~/.workbuddy/projects`` (see :mod:`memu.hosts.bridging`), *inject* as
a standing instruction in ``~/.workbuddy/MEMORY.md`` that points the agent at
the ``memu-workbuddy retrieve`` command.
"""

from memu.hosts.workbuddy.sessions import WorkBuddyTranscriptSource

__all__ = ["WorkBuddyTranscriptSource"]
