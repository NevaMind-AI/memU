"""The Hermes Agent host adapter — ``memu-hermes``.

Uses the active Hermes home's SQLite session store for explicit bridging
commands and a managed SOUL.md block for on-demand retrieval. The adapter
communicates through CLI commands and does not import Hermes's Python modules.
"""

from memu.hosts.hermes.sessions import HermesTranscriptSource

__all__ = ["HermesTranscriptSource"]
