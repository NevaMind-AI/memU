"""Cursor's agent transcripts: ``~/.cursor/projects/<escaped-cwd>/agent-transcripts/<id>/<id>.jsonl``.

The whole of what makes this host Cursor. Everything the bridging task does with
these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.

This is the **Cursor Agent** log (the CLI and background agents) — one directory
per project (the project's absolute path with ``/`` flattened to ``-``), one
transcript directory per session under ``agent-transcripts/``. The IDE's Composer
chats live elsewhere, inside the editor's ``state.vscdb`` SQLite state, and are
not read here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.cursor/projects"


class CursorTranscriptSource(TranscriptSource):
    """Cursor writes one JSON object per line: ``{"role": …, "message": {"content": […]}}``.

    A record is a conversation turn when its content carries a ``text`` block
    (user queries, and the assistant's prose — which often shares a record with
    the ``tool_use`` blocks it narrates), and a tool record when it carries only
    ``tool_use``/``tool_result`` blocks. Records carry no timestamps, so the
    cursor manifest records ``null`` there — the line count alone drives
    incremental scans.
    """

    name: ClassVar[str] = "cursor"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def discover(self) -> list[Path]:
        """Only ``agent-transcripts`` JSONL files — the project dirs also hold
        canvases, terminal logs, and whatever Cursor adds next."""
        root = self.root()
        if not root.is_dir():
            return []
        files = [path for path in root.glob("*/agent-transcripts/**/*.jsonl") if path.is_file()]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return files

    def classify(self, record: str) -> RecordKind:
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict) or entry.get("role") not in ("user", "assistant"):
            return RecordKind.OTHER

        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return RecordKind.MESSAGE
        if not isinstance(content, list):
            return RecordKind.OTHER

        kinds = {block.get("type") for block in content if isinstance(block, dict)}
        if "text" in kinds:
            return RecordKind.MESSAGE
        if kinds & {"tool_use", "tool_result"}:
            return RecordKind.TOOL
        return RecordKind.OTHER
