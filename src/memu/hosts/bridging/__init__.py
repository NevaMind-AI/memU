"""The bridging pipeline — host-agnostic, shared by every host adapter.

This is the *record* seam of ADR 0008, realized as a scheduled task: walk the
turns a host has logged since the last run, mine them into durable memory and
skills, and commit the result. A host contributes only a
:class:`~memu.hosts.base.TranscriptSource`; the cursor, the job templates, the
snapshot/diff, and the commit are all here and are not reimplemented per host.
"""

from memu.hosts.bridging.layout import Layout
from memu.hosts.bridging.pipeline import commit, prepare

__all__ = ["Layout", "commit", "prepare"]
