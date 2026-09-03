"""Hermes Agent's session log: the SQLite store at ``~/.hermes/state.db``.

The whole of what makes this host Hermes. Everything the bridging task does with
these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.

Hermes is the one supported host whose log is *only* ever SQLite, never
JSONL-on-disk (OpenClaw reads both): sessions and
their full message history live in two tables (``sessions``, ``messages``) of a
WAL-mode SQLite database under the Hermes home (``~/.hermes`` by default; the
host honors ``HERMES_HOME``, in which case pass ``--session-dir`` pointing at
that ``state.db``). ``~/.hermes/sessions/saved/`` holds only manual snapshots and
is ignored. This is exactly the "different container" seam
:class:`~memu.hosts.base.TranscriptSource` anticipates: :meth:`discover`,
:meth:`read_records`, :meth:`key`, and :meth:`timestamp` are overridden; each
session row plays the role a session *file* plays elsewhere, and each message row
is serialized to one JSON record so :meth:`classify` still sees one record at a
time.

The line-count cursor stays sound: messages are append-only per session, and
sessions are discovered most-recently-active first, so the scan's early stop at
the first unchanged session cannot hide newer content.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

STATE_DB = "~/.hermes/state.db"


def state_db_path() -> Path:
    """Resolve the active Hermes session store using Hermes's own precedence."""
    if value := os.environ.get("HERMES_HOME", "").strip():
        return Path(value) / "state.db"
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        root = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return root / "hermes" / "state.db"
    return Path.home() / ".hermes" / "state.db"


_MESSAGE_ROLES = ("user", "assistant")

# Hermes already projects SQLite rows to _ROW_COLUMNS. Keep that OpenAI-shaped
# dialect forward-compatible by deleting only known runtime/provider replay
# fields from the projected record and its serialized tool calls.
_ROW_PRIVATE_FIELDS = frozenset({"timestamp"})
_TOOL_CALL_PRIVATE_FIELDS = frozenset({"call_id", "response_item_id", "extra_content"})

_ROW_COLUMNS = ("role", "content", "tool_call_id", "tool_calls", "tool_name", "timestamp")


def _drop_known_fields(value: dict[object, object], fields: frozenset[str]) -> bool:
    """Delete only known private fields; unknown fields are intentionally retained."""
    changed = False
    for field in fields:
        if field in value:
            del value[field]
            changed = True
    return changed


def _sanitize_tool_calls(value: object) -> tuple[object, bool]:
    tool_calls = value
    if isinstance(value, str):
        try:
            tool_calls = json.loads(value)
        except json.JSONDecodeError:
            return value, False
    if not isinstance(tool_calls, list):
        return value, False

    changed = False
    for tool_call in tool_calls:
        if isinstance(tool_call, dict):
            changed |= _drop_known_fields(tool_call, _TOOL_CALL_PRIVATE_FIELDS)
    if not changed:
        return value, False
    return (json.dumps(tool_calls, ensure_ascii=False) if isinstance(value, str) else tool_calls), True


class HermesTranscriptSource(TranscriptSource):
    """Hermes stores OpenAI-shaped chat rows: ``role`` + ``content`` + tool columns.

    A row is a conversation turn when its role is user or assistant and it says
    something (non-empty ``content``); an assistant row that only carries
    ``tool_calls``, and every ``tool`` row (the call's output, keyed by
    ``tool_call_id``), is a tool record. System rows and anything else are noise
    the mining jobs should never see.
    """

    name: ClassVar[str] = "hermes"

    def __init__(self, state_db: str | Path | None = None) -> None:
        self._db = Path(os.path.expanduser(str(state_db))) if state_db is not None else state_db_path()

    def root(self) -> Path:
        return self._db.parent

    def exists(self) -> bool:
        return self._db.is_file()

    def key(self, path: Path) -> str:
        """Sessions have no path of their own — the cursor key is the session id."""
        return path.name

    def session_id(self, path: Path) -> str:
        """The virtual path's full name is Hermes's session id."""
        return path.name

    def _connect(self) -> sqlite3.Connection:
        # Read-only: the bridging task must never take Hermes's write lock —
        # the gateway and live CLI sessions share this database in WAL mode.
        # The path is percent-encoded into a proper file: URI — pasted in raw,
        # a '%' in the path would decode and a '#' would truncate it, silently
        # taking ?mode=ro (and the read-only guarantee) with it.
        return sqlite3.connect(f"{self._db.resolve().as_uri()}?mode=ro", uri=True)

    def discover(self) -> list[Path]:
        """Sessions with messages, most-recently-active first, as virtual paths.

        The paths never touch the filesystem — the pipeline only hands them back
        to :meth:`key` and :meth:`read_records`.
        """
        if not self.exists():
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id FROM messages GROUP BY session_id ORDER BY MAX(timestamp) DESC"
            ).fetchall()
        return [self.root() / session_id for (session_id,) in rows]

    def read_records(self, path: Path) -> list[str]:
        """One session's message rows, in insertion order, as JSON lines."""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_ROW_COLUMNS)} FROM messages WHERE session_id = ? ORDER BY id",  # noqa: S608
                (path.name,),
            ).fetchall()
        return [
            json.dumps(
                {column: value for column, value in zip(_ROW_COLUMNS, row, strict=True) if value is not None},
                ensure_ascii=False,
            )
            for row in rows
        ]

    def sanitize(self, path: Path, record: str) -> str:
        """Remove known runtime metadata from one projected SQLite row."""
        del path  # Required by the host seam; every Hermes session has the same row shape.
        try:
            row = json.loads(record)
        except json.JSONDecodeError:
            return record
        if not isinstance(row, dict):
            return record

        changed = _drop_known_fields(row, _ROW_PRIVATE_FIELDS)
        tool_calls, tool_calls_changed = _sanitize_tool_calls(row.get("tool_calls"))
        if tool_calls_changed:
            row["tool_calls"] = tool_calls
            changed = True

        return json.dumps(row, ensure_ascii=False) if changed else record

    def classify(self, record: str) -> RecordKind:
        try:
            row = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(row, dict):
            return RecordKind.OTHER

        role = row.get("role")
        if role == "tool":
            return RecordKind.TOOL
        if role in _MESSAGE_ROLES:
            if row.get("content"):
                return RecordKind.MESSAGE
            if row.get("tool_calls"):
                return RecordKind.TOOL
        return RecordKind.OTHER

    def timestamp(self, record: str) -> str | None:
        """Hermes stamps rows with epoch seconds; the cursor file wants a string."""
        try:
            value = json.loads(record).get("timestamp")
        except (json.JSONDecodeError, AttributeError):
            return None
        if isinstance(value, (int, float)):
            return datetime.datetime.fromtimestamp(value, tz=datetime.UTC).isoformat()
        return value if isinstance(value, str) else None
