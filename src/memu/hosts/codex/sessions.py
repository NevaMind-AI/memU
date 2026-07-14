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


class CodexTranscriptSource(TranscriptSource):
    """Codex writes one JSON object per line, each wrapping a ``payload``.

    A payload is a conversation turn when its ``type`` is ``message`` and its
    ``role`` is user or assistant, and a tool record when its ``type`` is a
    function call or a function-call output. Everything else — session metadata,
    reasoning traces — is noise the mining jobs should never see.
    """

    name: ClassVar[str] = "codex"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        try:
            payload = json.loads(record).get("payload")
        except (json.JSONDecodeError, AttributeError):
            return RecordKind.OTHER
        if not isinstance(payload, dict):
            return RecordKind.OTHER

        kind = payload.get("type")
        if kind == "message" and payload.get("role") in _MESSAGE_ROLES:
            return RecordKind.MESSAGE
        if kind in _TOOL_TYPES:
            return RecordKind.TOOL
        return RecordKind.OTHER
