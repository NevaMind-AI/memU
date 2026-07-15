"""The host seam: where a session log lives, and how to read one record of it.

This is deliberately the *only* abstraction between hosts. Everything else the
bridging task does — the per-session line cursor, the job-instruction templates,
the content-hash snapshot/diff of the mirrored recall files, the commit back into
memU — is host-agnostic and already lives in :mod:`memu.hosts.bridging`.

So a second host is a :class:`TranscriptSource` and a thin CLI, and nothing else.
If a host ever needs to fork the pipeline, that is a signal the seam is drawn in
the wrong place — widen this class rather than copying `bridging/`.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import ClassVar


class RecordKind(Enum):
    """Which of the two transcripts a session record belongs in.

    Each session is sliced into two files, because the two mining jobs want
    different things: the **memory** job reads the conversation alone (what the
    user said they want), while the **skill** job also needs the tool calls (how
    the work was actually done).
    """

    MESSAGE = "message"
    """A user or assistant turn — appears in both transcripts."""

    TOOL = "tool"
    """A tool call or its output — appears only in the full transcript."""

    OTHER = "other"
    """Anything else (session metadata, reasoning traces, …) — dropped."""


class TranscriptSource(ABC):
    """One host's on-disk session log.

    The defaults assume one JSON object per line, which is what both Codex and
    Claude Code write. A host with a different container overrides
    :meth:`discover`, :meth:`read_records`, and :meth:`timestamp`; a host that is
    merely *shaped* differently only needs :meth:`classify`.
    """

    name: ClassVar[str]
    """Short host id. Names the binary (``memu-codex``) and scopes the cursor file."""

    @abstractmethod
    def root(self) -> Path:
        """Absolute directory holding the raw session logs."""

    @abstractmethod
    def classify(self, record: str) -> RecordKind:
        """Bucket one raw record. This *is* the host's log schema — the real seam."""

    def discover(self) -> list[Path]:
        """Session files under :meth:`root`, most-recently-modified first.

        Newest-first is load-bearing: the cursor scan stops at the first
        already-seen file, which is only sound if no older file can hold newer
        content.
        """
        root = self.root()
        if not root.is_dir():
            return []
        files = [path for path in root.rglob("*.jsonl") if path.is_file()]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return files

    def read_records(self, path: Path) -> list[str]:
        """A session file's records, in order, as raw non-empty lines."""
        with path.open(encoding="utf-8") as handle:
            return [line for line in (raw.strip() for raw in handle) if line]

    def timestamp(self, record: str) -> str | None:
        """The record's timestamp, if it carries one. Recorded in the cursor file."""
        try:
            value = json.loads(record).get("timestamp")
        except (json.JSONDecodeError, AttributeError):
            return None
        return value if isinstance(value, str) else None

    def key(self, path: Path) -> str:
        """The cursor-file key for a session — its path relative to :meth:`root`."""
        return path.relative_to(self.root()).as_posix()
