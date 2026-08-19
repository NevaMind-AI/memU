"""Claude Code's bridge source: existing Claude Code sessions plus Cowork audits."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptRead, TranscriptSource
from memu.hosts.claude_code.sessions import ClaudeCodeTranscriptSource
from memu.hosts.cowork.sessions import CoworkTranscriptSource


class ClaudeDesktopTranscriptSource(TranscriptSource):
    """Merge Claude Code and Cowork records without merging their source contracts."""

    name: ClassVar[str] = "claude-code"

    def __init__(self, session_dir: str | Path, cowork_roots: list[str | Path] | None = None) -> None:
        self._code = ClaudeCodeTranscriptSource(session_dir)
        self._cowork = CoworkTranscriptSource(cowork_roots)

    def root(self) -> Path:
        return self._code.root()

    def exists(self) -> bool:
        return self._code.exists() or self._cowork.exists()

    def _source(self, path: Path) -> TranscriptSource:
        return self._cowork if any(path.is_relative_to(root) for root in self._cowork.roots) else self._code

    def discover(self) -> list[Path]:
        paths = [*self._code.discover(), *self._cowork.discover()]
        paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return paths

    def read_records(self, path: Path) -> list[str]:
        return self._source(path).read_records(path)

    def read_incremental(self, path: Path, previous: dict[str, object] | None) -> TranscriptRead:
        return self._source(path).read_incremental(path, previous)

    def classify(self, record: str) -> RecordKind:
        return self._code.classify(record)

    def timestamp(self, record: str) -> str | None:
        return self._code.timestamp(record)

    def key(self, path: Path) -> str:
        return self._source(path).key(path)

    def scan_region(self, path: Path) -> str:
        if self._source(path) is self._cowork:
            root = next(root for root in self._cowork.roots if path.is_relative_to(root))
            return f"cowork:{root}"
        return "claude-code"

    def session_id(self, path: Path) -> str:
        return self._source(path).session_id(path)
