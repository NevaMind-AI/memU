"""The Hermes Agent host adapter — ``memu-hermes``.

Binds ADR 0008's two seams onto Hermes: *record* as a scheduled bridging task
over the SQLite session store at ``~/.hermes/state.db`` (see
:mod:`memu.hosts.bridging`), *inject* as a standing instruction in
``~/.hermes/SOUL.md`` that points the agent at the ``memu-hermes retrieve``
command.
"""

from memu.hosts.hermes.sessions import HermesTranscriptSource

__all__ = ["HermesTranscriptSource"]
