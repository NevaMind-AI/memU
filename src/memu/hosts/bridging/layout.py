"""Where the bridging pipeline keeps its working state.

Prepare and commit must agree on every one of these paths. They used to agree by
duplicating the constants in two scripts under a ``# Must match prepare_jobs.py``
comment — a comment is not a mechanism. One object, one source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = "~/.memu"

TRACK_DIRS: dict[str, str] = {"memory": "memory", "skill": "skill"}
"""RecallFile ``track`` -> the subdirectory its files are mirrored into."""


@dataclass(frozen=True)
class Layout:
    """The ``~/.memu`` working tree for one host's bridging runs."""

    base: Path
    host: str

    @classmethod
    def default(cls, host: str, base: str | Path = BASE_DIR) -> Layout:
        return cls(base=Path(os.path.expanduser(str(base))), host=host)

    @property
    def sessions(self) -> Path:
        """Transcripts sliced out of the host's session log this run."""
        return self.base / "sessions"

    @property
    def jobs(self) -> Path:
        """The numbered job-instruction files the agent works through."""
        return self.base / "jobs"

    @property
    def memory(self) -> Path:
        return self.base / TRACK_DIRS["memory"]

    @property
    def skill(self) -> Path:
        return self.base / TRACK_DIRS["skill"]

    @property
    def session_manifest(self) -> Path:
        """Per-session line cursor. Scoped by host: two hosts' session keys are
        unrelated, and sharing one cursor file would let each hide the other's
        new turns."""
        return self.base / f".session_manifest.{self.host}.json"

    @property
    def memory_manifest(self) -> Path:
        """Content hashes of the mirrored recall files, as of prepare."""
        return self.base / ".memory_manifest.json"

    @property
    def resource_log(self) -> Path:
        """Raw append-only log of files the sessions touched, written by the skill jobs."""
        return self.base / ".resource.tmp"

    @property
    def resources(self) -> Path:
        """The verified, describe-me resource file the agent annotates."""
        return self.base / "resources.md"

    @property
    def track_dirs(self) -> list[str]:
        return list(TRACK_DIRS.values())
