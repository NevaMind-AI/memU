"""Bridging run files and stable host cursor state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from memu.run import TRACK_DIRS as TRACK_DIRS
from memu.run import RunWorkspace

BASE_DIR = "~/.memu"


@dataclass(frozen=True)
class Layout(RunWorkspace):
    """A shared run workspace with host-owned progress and identity state.

    Callers serialize the entire cycle for ``state``; separate directories do
    not claim input. Existing hosts keep both roots at ``base``.
    """

    host: str
    state_base: Path | None = None

    @classmethod
    def default(cls, host: str, base: str | Path = BASE_DIR) -> Layout:
        return cls(base=Path(os.path.expanduser(str(base))), host=host)

    @property
    def state(self) -> Path:
        return self.state_base if self.state_base is not None else self.base

    @property
    def sessions(self) -> Path:
        return self.input

    @property
    def session_manifest(self) -> Path:
        """Successful host progress, advanced only after backend acknowledgement."""
        return self.state / f".session_manifest.{self.host}.json"

    @property
    def session_manifest_pending(self) -> Path:
        """This run's observed progress, still uncommitted."""
        return self.base / (self.session_manifest.name + ".pending")

    @property
    def run_marker(self) -> Path:
        return self.base / f".bridging_run.{self.host}.json"

    @property
    def self_sessions(self) -> Path:
        return self.state / f".self_sessions.{self.host}.json"

    @property
    def memory_manifest(self) -> Path:
        return self.manifest
