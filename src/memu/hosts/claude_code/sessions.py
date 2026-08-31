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
from memu.hosts.claude_records import classify_claude_record

SESSION_DIR = "~/.claude/projects"

_RECORD_PRIVATE_FIELDS = frozenset({
    "attributionMcpServer",
    "attributionMcpTool",
    "attributionSkill",
    "cwd",
    "effort",
    "entrypoint",
    "gitBranch",
    "isCompactSummary",
    "isMeta",
    "isSidechain",
    "isVisibleInTranscriptOnly",
    "origin",
    "parentUuid",
    "permissionMode",
    "promptId",
    "promptSource",
    "sessionId",
    "sourceToolAssistantUUID",
    "sourceToolUseID",
    "timestamp",
    "toolDenialKind",
    "toolUseResult",
    "userType",
    "uuid",
    "version",
})
_MESSAGE_PRIVATE_FIELDS = frozenset({"id", "model", "stop_details", "stop_reason", "usage"})


class ClaudeCodeTranscriptSource(TranscriptSource):
    """Claude Code writes one JSON object per line, usually one content block per record.

    A record whose ``type`` is ``user`` or ``assistant`` wraps an API-shaped
    ``message``; its content blocks say what the record is. Most records carry a
    single block, but multi-block records occur in real logs (``text`` alongside
    the ``tool_use`` calls it narrates, ``thinking`` alongside ``tool_use``) — a
    ``text`` block wins. ``text`` (or a plain-string user message) is a
    conversation turn; ``tool_use`` and ``tool_result`` are the tool record and
    its output — Claude Code logs the result as a *user*-typed record, so the
    role alone cannot classify. Everything else — ``thinking`` blocks,
    meta-injected user records (``isMeta``), and the non-message types
    (``queue-operation``, ``attachment``, ``system``, ``pr-link``,
    ``last-prompt``, ``summary``) — is noise the mining jobs should never see.
    """

    name: ClassVar[str] = "claude-code"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def session_id(self, path: Path) -> str:
        """The session that *owns* this transcript, which is not always its name.

        Subagent transcripts nest under the session that spawned them, and the
        nesting has more than one shape — on a real machine
        (703 transcripts) they are ``<slug>/<sessionId>/subagents/agent-<id>.jsonl``
        and ``<slug>/<sessionId>/subagents/workflows/wf_<id>/agent-<id>.jsonl``.
        So the owner is not the parent directory, which is ``subagents`` or a
        workflow id; it is always the *first* directory under the project slug.
        Reading it positionally that way also survives whatever level Claude Code
        adds next.

        The owner is what matters for skipping a bridging run (#606): if a run
        spawns a subagent, the child's transcript is just as much memU's own
        bookkeeping as the parent's.
        """
        parts = path.relative_to(self.root()).parts
        return parts[1] if len(parts) > 2 else path.stem

    def classify(self, record: str) -> RecordKind:
        return classify_claude_record(record)

    def sanitize(self, path: Path, record: str) -> str:
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

        message = entry.get("message")
        if isinstance(message, dict):
            for field in _MESSAGE_PRIVATE_FIELDS:
                if field in message:
                    del message[field]
                    changed = True

        return json.dumps(entry, ensure_ascii=False) if changed else record
