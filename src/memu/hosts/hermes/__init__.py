"""The Hermes Agent host adapter — ``memu-hermes``.

Binds ADR 0008's two seams onto Hermes: *record* as a scheduled bridging task
over the SQLite session store at ``$HERMES_HOME/state.db`` (see
:mod:`memu.hosts.bridging`), *inject* as a standing instruction in
``$HERMES_HOME/SOUL.md`` that points the agent at the ``memu-hermes retrieve``
command.
"""

from memu.hosts.hermes.sessions import HermesTranscriptSource

__all__ = ["HermesTranscriptSource"]
