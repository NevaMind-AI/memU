"""OpenClaw's session transcripts: ``~/.openclaw/agents/<agentId>/sessions/*.jsonl``.

The whole of what makes this host OpenClaw. Everything the bridging task does
with these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.

One transcript per session, named by session id (Telegram topic sessions add a
``-topic-<threadId>`` suffix), grouped per agent under the OpenClaw state dir
(``~/.openclaw`` by default; the host honors ``OPENCLAW_STATE_DIR``, in which
case pass ``--session-dir``). The mutable ``sessions.json`` index sitting next to
the transcripts is not JSONL and is naturally skipped by discovery. Newer
OpenClaw builds can keep transcripts in SQLite instead (a ``sqlite:`` session
target); those are out of this adapter's reach — it reads the JSONL default.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.openclaw/agents"

_MESSAGE_ROLES = ("user", "assistant")


class OpenClawTranscriptSource(TranscriptSource):
    """OpenClaw writes one JSON object per line, in a parent-linked entry tree.

    An entry is a conversation turn when its ``type`` is ``message`` and its
    ``message.role`` is user or assistant (assistant entries carry their tool
    calls inline as content blocks), and a tool record when the role is
    ``toolResult`` — the tool output comes back as its own entry. Everything
    else — the ``session`` header, ``compaction`` summaries, ``custom`` extension
    state, model/thinking change markers — is noise the mining jobs should never
    see.
    """

    name: ClassVar[str] = "openclaw"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict) or entry.get("type") != "message":
            return RecordKind.OTHER

        message = entry.get("message")
        role = message.get("role") if isinstance(message, dict) else None
        if role in _MESSAGE_ROLES:
            return RecordKind.MESSAGE
        if role == "toolResult":
            return RecordKind.TOOL
        return RecordKind.OTHER

    def timestamp(self, record: str) -> str | None:
        """OpenClaw stamps entries with either an ISO string or epoch millis."""
        try:
            value = json.loads(record).get("timestamp")
        except (json.JSONDecodeError, AttributeError):
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 1e11 else value
            return datetime.datetime.fromtimestamp(seconds, tz=datetime.UTC).isoformat()
        return None
