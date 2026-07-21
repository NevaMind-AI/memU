"""Slice the turns a host has logged since the last run into numbered transcripts.

Host-agnostic: everything specific to *this* host's log — where it is, how a
record is shaped — arrives through :class:`~memu.hosts.base.TranscriptSource`.
"""

from __future__ import annotations

import json
from pathlib import Path

from memu.hosts.base import RecordKind, TranscriptSource


def _split(source: TranscriptSource, records: list[str]) -> tuple[list[str], list[str]]:
    """Partition records into (conversation only, conversation + tool calls)."""
    messages: list[str] = []
    full: list[str] = []
    for record in records:
        kind = source.classify(record)
        if kind is RecordKind.MESSAGE:
            messages.append(record)
            full.append(record)
        elif kind is RecordKind.TOOL:
            full.append(record)
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
) -> int:
    """Extract new session turns into numbered transcripts and *stage* the cursor.

    Scans the host's sessions newest-first, comparing each file's line count
    against the promoted cursor at ``manifest_path``. The first already-seen
    file with no new lines ends the scan — older files cannot hold newer
    content. The latest ``max_jobs`` files with new lines are written
    oldest-first as ``<idx>.jsonl`` (conversation) and ``<idx>_full.jsonl``
    (conversation plus tool calls), with ``idx`` from 1.

    The promoted cursor is read here but never written: the advanced cursor
    goes to ``pending_path``, and only a successful ``commit`` promotes it. So
    a bare ``prepare`` — or a run that dies before commit — leaves the durable
    cursor untouched, and every unmined turn stays selectable next time.

    Returns the number of sessions written. Zero is the correct, common outcome
    on a quiet day.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    pending: list[tuple[str, list[str], int]] = []
    for path in source.discover():
        key = source.key(path)
        previous = manifest.get(key)
        seen_lines = previous["lines"] if previous else 0

        records = source.read_records(path)
        if len(records) > seen_lines:
            pending.append((key, records, seen_lines))
        elif previous is not None:
            # Already recorded and unchanged; older files cannot be newer either.
            break

    # Keep the latest max_jobs, then emit oldest-first so idx counts up with mtime.
    selected = pending[:max_jobs]
    selected.reverse()

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.jsonl"):
        stale.unlink()

    for idx, (key, records, seen_lines) in enumerate(selected, start=1):
        messages, full = _split(source, records[seen_lines:])

        (out_dir / f"{idx}.jsonl").write_text("\n".join(messages) + "\n", encoding="utf-8")
        (out_dir / f"{idx}_full.jsonl").write_text("\n".join(full) + "\n", encoding="utf-8")

        manifest[key] = {"lines": len(records), "last_timestamp": _last_timestamp(source, records)}

    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return len(selected)
