"""Slice the turns a host has logged since the last run into numbered transcripts.

Host-agnostic: everything specific to *this* host's log — where it is, how a
record is shaped — arrives through :class:`~memu.hosts.base.TranscriptSource`.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from memu.hosts.base import RecordKind, TranscriptRead, TranscriptReadError, TranscriptSource

logger = logging.getLogger(__name__)

_PROBE_SESSIONS = 3
_PROBE_RECORDS_PER_SESSION = 200


@dataclass(frozen=True)
class TranscriptProbe:
    """Read-only sample of whether discovered sessions contain a known dialect."""

    sessions: int
    sampled_records: int
    recognized_records: int


def probe_transcripts(
    source: TranscriptSource,
    *,
    skip_sessions: Collection[str] = (),
    max_sessions: int = _PROBE_SESSIONS,
    max_records_per_session: int = _PROBE_RECORDS_PER_SESSION,
) -> TranscriptProbe:
    """Sample discovered sessions without advancing cursors or raising read failures.

    This is the bounded diagnostic used when ``prepare`` returns zero. It asks a
    different question from the incremental scan: did the host still write records
    this adapter recognizes? A read failure is inconclusive and is left to the
    existing per-session warning, rather than being mistaken for an unknown dialect.
    """
    skip = set(skip_sessions)
    sessions = 0
    sampled_records = 0
    recognized_records = 0

    try:
        paths = source.discover()
    except (OSError, sqlite3.Error, TranscriptReadError):
        # Discovery already failed open in the main prepare path. The probe is
        # diagnostic-only, so it must not turn that recoverable failure into a crash.
        return TranscriptProbe(sessions=0, sampled_records=0, recognized_records=0)

    for path in paths:
        if source.session_id(path) in skip:
            continue
        try:
            records = source.read_records(path)
        except (OSError, UnicodeDecodeError, TranscriptReadError):
            continue

        sessions += 1
        for record in records[:max_records_per_session]:
            # A newer SQLite schema can carry a compressed payload instead of text.
            # Treat that as unreadable-by-this-adapter, not as an empty transcript.
            if not isinstance(record, str):
                continue
            sampled_records += 1
            if source.classify(record) is not RecordKind.OTHER:
                recognized_records += 1

        if sessions >= max_sessions:
            break

    return TranscriptProbe(
        sessions=sessions,
        sampled_records=sampled_records,
        recognized_records=recognized_records,
    )


def _split(source: TranscriptSource, path: Path, records: list[str]) -> tuple[list[str], list[str]]:
    """Partition records into (conversation only, conversation + tool calls)."""
    messages: list[str] = []
    full: list[str] = []
    for record in records:
        kind = source.classify(record)
        if kind is RecordKind.MESSAGE:
            clean = source.sanitize(path, record)
            messages.append(clean)
            full.append(clean)
        elif kind is RecordKind.TOOL:
            full.append(source.sanitize(path, record))
    return messages, full


def _last_timestamp(source: TranscriptSource, records: list[str]) -> str | None:
    for record in reversed(records):
        if stamp := source.timestamp(record):
            return stamp
    return None


def prepare_transcripts(
    source: TranscriptSource,
    out_dir: Path,
    manifest_path: Path,
    max_jobs: int,
    pending_path: Path,
    skip_sessions: Collection[str] = (),
) -> int:
    """Extract new session turns into numbered transcripts and *stage* the cursor.

    Scans the host's sessions newest-first, asking each source to interpret its
    promoted cursor at ``manifest_path``. Append-only sources use a line count;
    sources with rewrite generations can invalidate that offset. The first
    already-seen session with no new records ends the scan — older sessions cannot
    hold newer activity. Sessions whose new records are all ``OTHER`` are staged as
    seen but do not consume job capacity. The latest ``max_jobs`` sessions with
    mineable records are written oldest-first as ``<idx>.jsonl`` (conversation)
    and ``<idx>_full.jsonl`` (conversation plus tool calls), with ``idx`` from 1.

    The promoted cursor is read here but never written: the advanced cursor
    goes to ``pending_path``, and only a successful ``commit`` promotes it. So
    a bare ``prepare`` — or a run that dies before commit — leaves the durable
    cursor untouched, and every unmined turn stays selectable next time.

    ``skip_sessions`` holds the ids of the bridging runs' own sessions
    (:mod:`memu.hosts.bridging.self_sessions`). They are passed over rather than
    ending the scan: they are the newest transcripts on disk, so stopping there
    would hide every real session underneath them.

    Returns the number of sessions written. Zero is the common outcome on a quiet
    day; the CLI separately distinguishes that from discovered sessions whose
    records all classify as ``OTHER``.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    skip = set(skip_sessions)

    pending: list[tuple[Path, str, TranscriptRead]] = []
    observed: dict[str, dict[str, object]] = {}
    stopped_regions: set[str] = set()
    for path in source.discover():
        region = source.scan_region(path)
        if region in stopped_regions:
            continue
        if source.session_id(path) in skip:
            continue
        key = source.key(path)
        previous = manifest.get(key)

        try:
            read = source.read_incremental(path, previous)
        except TranscriptReadError as exc:
            logger.warning("skipping unreadable transcript %s: %s", key, exc.cause)
            continue
        if read.changed and not any(
            source.classify(record) is not RecordKind.OTHER for record in read.records[read.start :]
        ):
            observed[key] = {**read.cursor, "last_timestamp": _last_timestamp(source, read.records)}
        elif read.changed and len(pending) < max_jobs:
            pending.append((path, key, read))
        elif not read.changed and previous is not None:
            # Already recorded and unchanged; older sessions in this region cannot be newer.
            stopped_regions.add(region)

    # Keep the latest max_jobs, then emit oldest-first so idx counts up with mtime.
    selected = pending[:max_jobs]
    selected.reverse()

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.jsonl"):
        stale.unlink()

    for idx, (path, key, read) in enumerate(selected, start=1):
        messages, full = _split(source, path, read.records[read.start :])
        (out_dir / f"{idx}.jsonl").write_text("\n".join(messages) + "\n", encoding="utf-8")
        (out_dir / f"{idx}_full.jsonl").write_text("\n".join(full) + "\n", encoding="utf-8")

        manifest[key] = {**read.cursor, "last_timestamp": _last_timestamp(source, read.records)}

    manifest.update(observed)

    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return len(selected)
