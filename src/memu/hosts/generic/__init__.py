"""The generic host adapter — ``memu-agent``, for agents without a dedicated one.

Binds ADR 0008's two seams onto any agent it can: *record* over a sniffed JSONL
session log (see :mod:`memu.hosts.generic.sessions`), *inject* into whatever
instruction file the agent loads. ``memu-agent detect`` is the entry point — it
finds both and says which seams work.
"""

from memu.hosts.generic.detect import Probe, probe, scan_home
from memu.hosts.generic.sessions import GenericTranscriptSource

__all__ = ["GenericTranscriptSource", "Probe", "probe", "scan_home"]
