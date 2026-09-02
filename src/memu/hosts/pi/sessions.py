"""pi v3 session transcripts: ``~/.pi/agent/sessions/<encoded-cwd>/*.jsonl``."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

AGENT_DIR = os.environ.get("PI_CODING_AGENT_DIR", "~/.pi/agent")
SESSION_DIR = os.environ.get("PI_CODING_AGENT_SESSION_DIR", f"{AGENT_DIR}/sessions")

# Delete-only: unknown record, message, and content-block fields are preserved.
_RECORD_PRIVATE_FIELDS = frozenset({"id", "parentId", "timestamp"})
_MESSAGE_PRIVATE_FIELDS = frozenset({
    "api",
    "errorMessage",
    "model",
    "provider",
    "rawStopReason",
    "responseId",
    "stopReason",
    "timestamp",
    "usage",
})
_TOOL_RESULT_PRIVATE_FIELDS = frozenset({"details"})
_BLOCK_PRIVATE_FIELDS = frozenset({"thinkingSignature"})


def _drop_known_fields(value: dict[object, object], fields: frozenset[str]) -> bool:
    changed = False
    for field in fields:
        if field in value:
            del value[field]
            changed = True
    return changed


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

    def sanitize(self, path: Path, record: str) -> str:
        """Remove known Pi runtime metadata from prepared transcript output."""
        del path  # Required by the host seam; every Pi session has the same record shape.
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return record
        if not isinstance(entry, dict):
            return record

        changed = _drop_known_fields(entry, _RECORD_PRIVATE_FIELDS)
        message = entry.get("message")
        if not isinstance(message, dict):
            return json.dumps(entry, ensure_ascii=False) if changed else record

        changed |= _drop_known_fields(message, _MESSAGE_PRIVATE_FIELDS)
        if message.get("role") == "toolResult":
            changed |= _drop_known_fields(message, _TOOL_RESULT_PRIVATE_FIELDS)

        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    changed |= _drop_known_fields(block, _BLOCK_PRIVATE_FIELDS)

        return json.dumps(entry, ensure_ascii=False) if changed else record

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
