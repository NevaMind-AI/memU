"""pi v3 session transcripts: ``~/.pi/agent/sessions/<encoded-cwd>/*.jsonl``."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

AGENT_DIR = os.environ.get("PI_CODING_AGENT_DIR", "~/.pi/agent")
SESSION_DIR = os.environ.get("PI_CODING_AGENT_SESSION_DIR", f"{AGENT_DIR}/sessions")


class PiTranscriptSource(TranscriptSource):
    """Split pi's parent-linked message entries into conversation and tool tracks."""

    name: ClassVar[str] = "pi"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def session_id(self, path: Path) -> str:
        """Return the UUID Pi exports, without its filename timestamp prefix."""
        return path.stem.rsplit("_", 1)[-1]

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
        if role in {"toolResult", "bashExecution"}:
            return RecordKind.TOOL
        if role not in {"user", "assistant"}:
            return RecordKind.OTHER

        content = message.get("content")
        if isinstance(content, str):
            return RecordKind.MESSAGE
        if not isinstance(content, list):
            return RecordKind.OTHER
        block_types = {block.get("type") for block in content if isinstance(block, dict)}
        if "text" in block_types:
            return RecordKind.MESSAGE
        if "toolCall" in block_types:
            return RecordKind.TOOL
        return RecordKind.OTHER
