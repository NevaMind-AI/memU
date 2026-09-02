"""Slice the turns a host has logged since the last run into numbered transcripts.

Host-agnostic: everything specific to *this* host's log — where it is, how a
record is shaped — arrives through :class:`~memu.hosts.base.TranscriptSource`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Collection
from pathlib import Path

from memu.hosts.base import RecordKind, TranscriptRead, TranscriptReadError, TranscriptSource

logger = logging.getLogger(__name__)


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

    Returns the number of sessions written. Zero is the correct, common outcome
    on a quiet day.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    skip = set(skip_sessions)

    pending: list[tuple[Path, str, TranscriptRead, list[str], list[str]]] = []
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
        if read.changed:
            messages, full = _split(source, path, read.records[read.start :])
            if full:
                pending.append((path, key, read, messages, full))
            else:
                observed[key] = {**read.cursor, "last_timestamp": _last_timestamp(source, read.records)}
        elif previous is not None:
            # Already recorded and unchanged; older sessions in this region cannot be newer.
            stopped_regions.add(region)

    # Keep the latest max_jobs, then emit oldest-first so idx counts up with mtime.
    selected = pending[:max_jobs]
    selected.reverse()

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.jsonl"):
        stale.unlink()

    for idx, (_path, key, read, messages, full) in enumerate(selected, start=1):
        (out_dir / f"{idx}.jsonl").write_text("\n".join(messages) + "\n", encoding="utf-8")
        (out_dir / f"{idx}_full.jsonl").write_text("\n".join(full) + "\n", encoding="utf-8")

        manifest[key] = {**read.cursor, "last_timestamp": _last_timestamp(source, read.records)}

    manifest.update(observed)

    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return len(selected)
