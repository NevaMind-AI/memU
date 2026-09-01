"""Codex's session log: ``~/.codex/sessions/**/*.jsonl``.

The whole of what makes this host Codex. Everything the bridging task does with
these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.codex/sessions"

_MESSAGE_ROLES = ("user", "assistant")
_TOOL_TYPES = ("function_call", "function_call_output")

# Keep Codex's response-item dialect forward-compatible: these sets are
# delete-only. Unknown envelope, payload, and content-item fields are preserved.
_RECORD_PRIVATE_FIELDS = frozenset({"timestamp"})
_PAYLOAD_PRIVATE_FIELDS = frozenset({"id", "internal_chat_message_metadata_passthrough"})

# Harness-injected context is logged as ordinary user messages with no
# isMeta-style flag; the leading marker is the only thing that distinguishes it
# from typing. The layout drifts across versions — 0.80.0 writes AGENTS.md and
# environment_context as standalone records, 0.124.x packs both into one
# record's items — so the check is per item, not per record.
_INJECTED_PREFIXES = (
    "<environment_context>",
    "<turn_aborted>",
    "# AGENTS.md instructions for",
)


def _injected(payload: dict) -> bool:
    """True when every content item is harness-injected context, none typing."""
    if payload.get("role") != "user":
        return False
    content = payload.get("content")
    if not isinstance(content, list):
        return False
    texts = [item.get("text", "") for item in content if isinstance(item, dict)]
    return bool(texts) and all(text.lstrip().startswith(_INJECTED_PREFIXES) for text in texts)


class CodexTranscriptSource(TranscriptSource):
    """Codex writes one JSON object per line, each wrapping a ``payload``.

    A payload is a conversation turn when its ``type`` is ``message`` and its
    ``role`` is user or assistant — unless it is harness context wearing the
    user role: Codex logs ``<environment_context>`` dumps, ``<turn_aborted>``
    markers, and AGENTS.md instructions as ordinary user messages, so a user
    record whose every content item opens with a known injection marker is
    dropped (any item of real prose keeps the record; an unknown future marker
    leaks rather than costing a real message). A payload is a tool record when
    its ``type`` is a function call or a function-call output. Everything else —
    session metadata, reasoning traces — is noise the mining jobs should never
    see.
    """

    name: ClassVar[str] = "codex"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def sanitize(self, path: Path, record: str) -> str:
        """Remove known runtime metadata without projecting the response item."""
        del path  # Required by the host seam; every Codex session has the same record shape.
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return record
        if not isinstance(entry, dict):
            return record

        changed = False
        for field in _RECORD_PRIVATE_FIELDS:
            if field in entry:
                del entry[field]
                changed = True

        payload = entry.get("payload")
        if isinstance(payload, dict):
            for field in _PAYLOAD_PRIVATE_FIELDS:
                if field in payload:
                    del payload[field]
                    changed = True

        return json.dumps(entry, ensure_ascii=False) if changed else record

    def classify(self, record: str) -> RecordKind:
        try:
            payload = json.loads(record).get("payload")
        except (json.JSONDecodeError, AttributeError):
            return RecordKind.OTHER
        if not isinstance(payload, dict):
            return RecordKind.OTHER

        kind = payload.get("type")
        if kind == "message" and payload.get("role") in _MESSAGE_ROLES:
            return RecordKind.OTHER if _injected(payload) else RecordKind.MESSAGE
        if kind in _TOOL_TYPES:
            return RecordKind.TOOL
        return RecordKind.OTHER
