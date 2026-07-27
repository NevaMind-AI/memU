"""Cola session transcripts: ``~/.cola/sessions/<scope>/*.jsonl``.

Cola keeps one directory per session scope.  The JSONL stream contains a
``session`` header and model/thinking changes in addition to conversation rows;
only ``message`` rows are bridge input.  A message has a nested ``message``
object with ``role`` and block-list ``content``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.cola/sessions"


class ColaTranscriptSource(TranscriptSource):
    """Read Cola's JSONL conversations while dropping runtime metadata."""

    name: ClassVar[str] = "cola"

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
        if not isinstance(message, dict):
            return RecordKind.OTHER
        role = message.get("role")
        content = message.get("content")
        if not isinstance(content, list):
            return RecordKind.OTHER
        block_types = {block.get("type") for block in content if isinstance(block, dict)}

        if role == "toolResult":
            return RecordKind.TOOL
        if role in {"user", "assistant"}:
            # A narrated tool call remains a conversation turn; an otherwise
            # empty assistant tool-call row belongs to the full transcript.
            if "text" in block_types:
                return RecordKind.MESSAGE
            if "toolCall" in block_types:
                return RecordKind.TOOL
        return RecordKind.OTHER

    def timestamp(self, record: str) -> str | None:
        try:
            entry: Any = json.loads(record)
        except json.JSONDecodeError:
            return None
        if not isinstance(entry, dict):
            return None
        value = entry.get("timestamp")
        if not isinstance(value, str):
            message = entry.get("message")
            value = message.get("timestamp") if isinstance(message, dict) else None
        return value if isinstance(value, str) else None
