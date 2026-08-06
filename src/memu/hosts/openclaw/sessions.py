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

OpenClaw assigns every SQLite transcript a rewrite generation. Appends preserve
that token; destructive replacement rotates it and restarts ``seq`` at zero. The
adapter therefore keeps the legacy path key but augments its cursor with the
SQLite generation, so a rewrite invalidates the old line offset instead of
silently stranding new content behind it.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptRead, TranscriptReadError, TranscriptSource

logger = logging.getLogger(__name__)

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
        self._stored_paths: set[Path] = set()

    def root(self) -> Path:
        return self._root

    def session_id(self, path: Path) -> str:
        """Return the id OpenClaw exposes to the session's tool subprocesses.

        SQLite virtual paths and ordinary legacy files are named by the session
        id. Legacy topic transcripts append ``-topic-<threadId>`` to that id;
        the suffix identifies the topic, not a different host session.
        """
        return path.stem.split("-topic-", 1)[0]

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
        """Run one read-only query, distinguishing failure from no rows."""
        try:
            conn = self._connect(db)
        except sqlite3.Error as exc:
            raise TranscriptReadError(db, exc) from exc
        try:
            return conn.execute(sql, args).fetchall()
        except sqlite3.Error as exc:
            raise TranscriptReadError(db, exc) from exc
        finally:
            # Closed here rather than by a `with` block: that one commits a
            # transaction but leaves the handle open, and there is one database
            # per agent to open on every scan.
            conn.close()

    def _virtual_path(self, db: Path, session_id: str) -> Path:
        """Where a database-held session pretends to live.

        A session keeps the address it had as a file — ``<agentId>/sessions/
        <sessionId>.jsonl`` — because the legacy file name *was* the session id.
        So :meth:`key` needs no override, while :meth:`read_incremental` augments
        the existing manifest entry with the store's rewrite generation. The path
        is never opened.
        """
        return db.parent.parent / "sessions" / f"{session_id}{_SESSION_SUFFIX}"

    def _stored_session(self, path: Path) -> tuple[Path, str] | None:
        """``(database, session_id)`` if discovery found this stored session."""
        if path not in self._stored_paths:
            return None
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
            try:
                rows = self._query(
                    db,
                    "SELECT w.session_id, COALESCE(w.transcript_updated_at, MAX(e.created_at)) "
                    "FROM transcript_events AS e "
                    "JOIN session_windows AS w ON w.session_id = e.session_id "
                    "GROUP BY w.session_id, w.transcript_updated_at",
                )
            except TranscriptReadError as exc:
                logger.warning("skipping unreadable OpenClaw transcript store %s: %s", db, exc.cause)
                continue
            # Grouping over the events themselves is what keeps empty sessions
            # out: a session that holds no transcript event has no row here, so
            # it never occupies a prepare slot. Trajectory events live in their
            # own table and are unreachable from this one.
            # Use OpenClaw's transcript mutation clock, not only event timestamps:
            # maintenance rewrites can preserve old created_at values while still
            # rotating the generation. The fallback serves early migrated rows.
            stored.extend((last_at / 1000, self._virtual_path(db, session_id)) for session_id, last_at in rows)

        claimed = {path for _, path in stored}
        self._stored_paths = claimed
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
        """One session's entries, in order, as the raw JSON lines they were."""
        stored = self._stored_session(path)
        if stored is not None:
            db, session_id = stored
            rows = self._query(
                db,
                "SELECT event_json FROM transcript_events WHERE session_id = ? ORDER BY seq",
                session_id,
            )
            return [event_json for (event_json,) in rows]
        # A legacy file that was never imported, or a host that has not upgraded.
        return super().read_records(path)

    def read_incremental(self, path: Path, previous: dict[str, object] | None) -> TranscriptRead:
        """Use OpenClaw's rewrite generation to validate the SQLite row offset."""
        stored = self._stored_session(path)
        if stored is None:
            return super().read_incremental(path, previous)

        db, session_id = stored
        rows = self._query(
            db,
            "SELECT r.generation, e.event_json "
            "FROM transcript_rewrite_watermarks AS r "
            "LEFT JOIN transcript_events AS e ON e.session_id = r.session_id "
            "WHERE r.session_id = ? ORDER BY e.seq",
            session_id,
        )
        if not rows:
            error = sqlite3.DatabaseError(f"missing transcript generation for session {session_id}")
            raise TranscriptReadError(db, error) from error

        generation = rows[0][0]
        records = [event_json for _, event_json in rows if event_json is not None]
        previous_lines = previous.get("lines", 0) if previous else 0
        if not isinstance(previous_lines, int):
            previous_lines = 0
        previous_generation = previous.get("generation") if previous else None
        previous_container = previous.get("container") if previous else None

        # A rotated generation restarts seq at zero. A legacy JSONL cursor has no
        # generation or stable prefix identity either, so the first SQLite read
        # must make the same conservative choice: replay this generation once
        # rather than risk silently skipping rewritten content.
        same_generation = previous_container == "sqlite" and previous_generation == generation
        start = previous_lines if same_generation else 0

        return TranscriptRead(
            records=records,
            start=start,
            cursor={"container": "sqlite", "generation": generation, "lines": len(records)},
        )

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
