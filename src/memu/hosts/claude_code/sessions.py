"""Claude Code's session log: ``~/.claude/projects/<escaped-cwd>/*.jsonl``.

The whole of what makes this host Claude Code. Everything the bridging task does
with these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.

Claude Code keeps one directory per project — the project's absolute path with
``/`` flattened to ``-`` (``/Users/a/proj`` → ``-Users-a-proj``) — and one JSONL
file per session inside it, named by the session UUID. Subagent transcripts land
in a sibling subdirectory per session and are picked up by the same recursive
glob.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.claude/projects"


class ClaudeCodeTranscriptSource(TranscriptSource):
    """Claude Code writes one JSON object per line, one content block per record.

    A record whose ``type`` is ``user`` or ``assistant`` wraps an API-shaped
    ``message``; its single content block says what the record is. ``text`` (or a
    plain-string user message) is a conversation turn; ``tool_use`` and
    ``tool_result`` are the tool record and its output — Claude Code logs the
    result as a *user*-typed record, so the role alone cannot classify. Everything
    else — ``thinking`` blocks, meta-injected user records (``isMeta``), and the
    non-message types (``queue-operation``, ``attachment``, ``system``,
    ``pr-link``, ``last-prompt``, ``summary``) — is noise the mining jobs should
    never see.
    """

    name: ClassVar[str] = "claude-code"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict) or entry.get("type") not in ("user", "assistant"):
            return RecordKind.OTHER

        message = entry.get("message")
        if not isinstance(message, dict):
            return RecordKind.OTHER

        content = message.get("content")
        if isinstance(content, str):
            # A raw-string user message is the user actually typing; meta records
            # are harness-injected context wearing the user role.
            return RecordKind.OTHER if entry.get("isMeta") else RecordKind.MESSAGE

        kinds = (
            {block.get("type") for block in content if isinstance(block, dict)} if isinstance(content, list) else set()
        )
        if "text" in kinds:
            return RecordKind.OTHER if entry.get("isMeta") else RecordKind.MESSAGE
        if kinds & {"tool_use", "tool_result"}:
            return RecordKind.TOOL
        return RecordKind.OTHER
