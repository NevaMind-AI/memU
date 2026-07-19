"""WorkBuddy's session log: ``~/.workbuddy/projects/<escaped-cwd>/*.jsonl``.

The whole of what makes this host WorkBuddy. Everything the bridging task does
with these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.

WorkBuddy keeps one directory per project — the project's absolute path with
``/`` and ``\\`` flattened to ``-`` (``/Users/a/proj`` -> ``-Users-a-proj``) —
and one JSONL file per session inside it, named by the session UUID.  The
``sessions.json`` index sitting next to the project directories is not JSONL and
is naturally skipped by discovery.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.workbuddy/projects"

_MESSAGE_ROLES = ("user", "assistant")
_TOOL_TYPES = ("function_call", "function_call_result")


class WorkBuddyTranscriptSource(TranscriptSource):
    """WorkBuddy writes one JSON object per line, each a typed record.

    A record is a conversation turn when its ``type`` is ``message`` and its
    ``role`` is user or assistant — the content blocks use ``input_text``
    (user) and ``output_text`` (assistant) instead of the ``text``/``tool_use``
    convention other hosts share.  A record is a tool call or its result when
    its ``type`` is ``function_call`` or ``function_call_result`` — these are
    standalone records, not nested inside a message's content blocks (the same
    pattern Codex uses).  Everything else — ``reasoning`` traces,
    ``file-history-snapshot`` metadata, ``ai-title`` auto-titles — is noise the
    mining jobs should never see.
    """

    name: ClassVar[str] = "workbuddy"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict):
            return RecordKind.OTHER

        typ = entry.get("type")

        # MESSAGE: user or assistant turns with text content.
        if typ == "message" and entry.get("role") in _MESSAGE_ROLES:
            content = entry.get("content")
            if isinstance(content, list):
                block_types = {b.get("type") for b in content if isinstance(b, dict)}
                if block_types & {"input_text", "output_text"}:
                    return RecordKind.MESSAGE
            if isinstance(content, str) and content:
                return RecordKind.MESSAGE

        # TOOL: function calls and their results (standalone records).
        if typ in _TOOL_TYPES:
            return RecordKind.TOOL

        return RecordKind.OTHER

    def timestamp(self, record: str) -> str | None:
        """WorkBuddy stamps records with epoch milliseconds."""
        try:
            value = json.loads(record).get("timestamp")
        except (json.JSONDecodeError, AttributeError):
            return None
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 1e11 else value
            return datetime.datetime.fromtimestamp(seconds, tz=datetime.UTC).isoformat()
        return value if isinstance(value, str) else None
