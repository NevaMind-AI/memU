"""OpenClaw's session transcripts, in either of the two shapes it has shipped.

The whole of what makes this host OpenClaw. Everything the bridging task does
with these records is host-agnostic and lives in :mod:`memu.hosts.bridging`.

Sessions are grouped per agent under the OpenClaw state dir (``~/.openclaw`` by
default; the host honors ``OPENCLAW_STATE_DIR``, in which case pass
``--session-dir``), and there are two containers to read::

    <root>/<agentId>/agent/openclaw-agent.sqlite   # current: N agents, N databases
    <root>/<agentId>/sessions/<sessionId>.jsonl    # legacy: one file per session

Upstream ``refactor(sessions): remove file-era transcript runtime`` moved the
transcripts into the per-agent database. Both shapes are read, because a single
version of this adapter has to serve hosts on either side of that upgrade — and
the two are not exclusive: an install that upgrades keeps its old files, and one
that has not upgraded yet has no database. So :meth:`discover` returns *one*
merged, newest-first list, and :meth:`read_records` picks the container per
session.

The legacy ``sessions.json`` index sitting next to the transcripts is not JSONL
and is naturally skipped by discovery; the ``*.trajectory.jsonl`` and
``*.checkpoint.*.jsonl`` sidecars *are* JSONL and are skipped by name.

The line-count cursor stays sound in both shapes: ``transcript_events.seq`` is
allocated per session as ``MAX(seq)+1``, so rows are append-only exactly as file
lines were, and sessions are discovered most-recently-active first, so the scan's
early stop at the first unchanged session cannot hide newer content.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

SESSION_DIR = "~/.openclaw/agents"

_MESSAGE_ROLES = ("user", "assistant")

# Sidecar files sharing the legacy sessions directory. Trajectory files hold
# trace events — every record classifies OTHER, so scanning them fills prepare's
# max_jobs slots with empty transcripts (they touch on every turn, so
# newest-first keeps them on top). Checkpoint files re-emit turns the main
# session transcript already has, so the same conversation is mined twice.
#
# This filter is permanent, not a deprecation path: it is the *legacy* shape that
# grows these files, and hosts still on the file era keep writing them.
_SIDECAR_MARKERS = (".trajectory.", ".checkpoint.")

# The per-agent transcript database, and the directory upstream moves the
# imported legacy files into once they are inside it. The archive is excluded
# from discovery rather than deduped: its contents are already being read out of
# the database under the pre-upgrade cursor key (see :meth:`read_records`), so
# scanning it would re-mine the entire pre-upgrade history under a second key.
_STORE_SUBDIR = "agent"
_STORE_NAME = "openclaw-agent.sqlite"
_IMPORT_ARCHIVE_DIR = "session-sqlite-import-archive"

_SESSION_SUFFIX = ".jsonl"


class OpenClawTranscriptSource(TranscriptSource):
    """OpenClaw records a parent-linked entry tree, one JSON object per entry.

    An entry is a conversation turn when its ``type`` is ``message`` and its
    ``message.role`` is user or assistant (assistant entries carry their tool
    calls inline as content blocks), and a tool record when the role is
    ``toolResult`` — the tool output comes back as its own entry. Everything
    else — the ``session`` header, ``reset`` markers, ``custom`` extension state,
    model/thinking change markers — is noise the mining jobs should never see.

    :meth:`classify` and :meth:`timestamp` are shape, not container, and the
    move to SQLite did not change the shape: each ``transcript_events.event_json``
    is the entry object verbatim — the same string that used to be one line of
    the file. Only the container methods below know which store they came from.
    """

    name: ClassVar[str] = "openclaw"

    def __init__(self, session_dir: str | Path = SESSION_DIR) -> None:
        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    # ── containers ────────────────────────────────────────────────────────────

    def _databases(self) -> list[Path]:
        """Every agent's transcript database, one per agent directory."""
        if not self._root.is_dir():
            return []
        return sorted(path for path in self._root.glob(f"*/{_STORE_SUBDIR}/{_STORE_NAME}") if path.is_file())

    def _connect(self, db: Path) -> sqlite3.Connection:
        # Read-only: the bridging task must never take OpenClaw's write lock —
        # the gateway and live sessions share this database in WAL mode. The path
        # is percent-encoded into a proper file: URI — pasted in raw, a '%' in the
        # path would decode and a '#' would truncate it, silently taking
        # ?mode=ro (and the read-only guarantee) with it.
        return sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)

    def _query(self, db: Path, sql: str, *args: object) -> list[tuple]:
        """Run one read-only query, or return nothing if the store is unreadable.

        Fails open, deliberately: ``prepare`` runs unattended on a schedule, so a
        database that is locked, half-written, or on a schema this adapter does
        not recognize has to degrade to "this store contributes no sessions" —
        never to a crashed run that stops mining until someone notices.
        """
        try:
            conn = self._connect(db)
        except sqlite3.Error:
            return []
        try:
            return conn.execute(sql, args).fetchall()
        except sqlite3.Error:
            return []
        finally:
            # Closed here rather than by a `with` block: that one commits a
            # transaction but leaves the handle open, and there is one database
            # per agent to open on every scan.
            conn.close()

    def _virtual_path(self, db: Path, session_id: str) -> Path:
        """Where a database-held session pretends to live.

        A session keeps the address it had as a file — ``<agentId>/sessions/
        <sessionId>.jsonl`` — because the legacy file name *was* the session id.
        So :meth:`key` needs no override and the cursor survives the upgrade: a
        session mined to 120 records as a file resumes at record 121 as rows,
        with no manifest migration and no flag day. The path is never opened.
        """
        return db.parent.parent / "sessions" / f"{session_id}{_SESSION_SUFFIX}"

    def _stored_session(self, path: Path) -> tuple[Path, str] | None:
        """``(database, session_id)`` if this path addresses a stored session."""
        try:
            parts = path.relative_to(self._root).parts
        except ValueError:
            return None
        if len(parts) != 3 or parts[1] != "sessions" or not parts[2].endswith(_SESSION_SUFFIX):
            return None
        db = self._root / parts[0] / _STORE_SUBDIR / _STORE_NAME
        return (db, parts[2][: -len(_SESSION_SUFFIX)]) if db.is_file() else None

    # ── discovery ─────────────────────────────────────────────────────────────

    def discover(self) -> list[Path]:
        """Both shapes as one list, most-recently-active first.

        Ordering is load-bearing, and the two stores count time differently —
        SQLite in epoch milliseconds, files in ``st_mtime`` seconds. They are
        normalized to one scale before merging: compared raw, every database
        session would sort ahead of every file, and the scan's early stop would
        then hide real sessions behind them.
        """
        stored: list[tuple[float, Path]] = []
        for db in self._databases():
            rows = self._query(
                db,
                "SELECT session_id, MAX(created_at) FROM transcript_events GROUP BY session_id",
            )
            # Grouping over the events themselves is what keeps empty sessions
            # out: a session that holds no transcript event has no row here, so
            # it never occupies a prepare slot. Trajectory events live in their
            # own table and are unreachable from this one.
            stored.extend((last_at / 1000, self._virtual_path(db, session_id)) for session_id, last_at in rows)

        claimed = {path for _, path in stored}
        files = [
            (path.stat().st_mtime, path)
            for path in super().discover()
            if not any(marker in path.name for marker in _SIDECAR_MARKERS)
            and _IMPORT_ARCHIVE_DIR not in path.parts
            # A file still sitting next to a session already in the database:
            # same conversation, one cursor key. The database wins — it is the
            # live store, the file is a leftover that stopped being appended to.
            and path not in claimed
        ]

        merged = stored + files
        merged.sort(key=lambda entry: entry[0], reverse=True)
        return [path for _, path in merged]

    def read_records(self, path: Path) -> list[str]:
        """One session's entries, in order, as the raw JSON lines they were.

        Raw ``transcript_events`` rows rather than the active-events projection:
        the file carried the whole parent-linked tree including branches, so raw
        rows reproduce today's semantics exactly, and no rewind can make the
        visible count shrink underneath the line cursor.
        """
        stored = self._stored_session(path)
        if stored is not None:
            db, session_id = stored
            rows = self._query(
                db,
                "SELECT event_json FROM transcript_events WHERE session_id = ? ORDER BY seq",
                session_id,
            )
            if rows:
                return [event_json for (event_json,) in rows]
        # No such session in the store — a legacy file that was never imported,
        # or a host that has not upgraded at all.
        return super().read_records(path)

    # ── shape ─────────────────────────────────────────────────────────────────

    def classify(self, record: str) -> RecordKind:
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict) or entry.get("type") != "message":
            return RecordKind.OTHER

        message = entry.get("message")
        role = message.get("role") if isinstance(message, dict) else None
        if role in _MESSAGE_ROLES:
            return RecordKind.MESSAGE
        if role == "toolResult":
            return RecordKind.TOOL
        return RecordKind.OTHER

    def timestamp(self, record: str) -> str | None:
        """OpenClaw stamps entries with either an ISO string or epoch millis."""
        try:
            value = json.loads(record).get("timestamp")
        except (json.JSONDecodeError, AttributeError):
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 1e11 else value
            return datetime.datetime.fromtimestamp(seconds, tz=datetime.UTC).isoformat()
        return None
