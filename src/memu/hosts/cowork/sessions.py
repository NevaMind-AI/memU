"""Claude Cowork audit logs stored by Claude Desktop on Windows."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptReadError, TranscriptSource
from memu.hosts.claude_records import classify_claude_record

_AUDIT_DIR = "local-agent-mode-sessions"


def windows_data_roots() -> list[Path]:
    """Return known Claude Desktop data roots that exist on this Windows install."""
    if sys.platform != "win32":
        return []

    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    candidates = [
        appdata / "Claude",
        local_appdata / "Claude-3p",
        *local_appdata.glob("Packages/Claude_*/LocalCache/Roaming/Claude"),
    ]
    seen: set[Path] = set()
    roots: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_dir() and resolved not in seen:
            seen.add(resolved)
            roots.append(resolved)
    return roots


class CoworkTranscriptSource(TranscriptSource):
    """Read one user-visible Cowork workspace per ``local_*/audit.jsonl`` file."""

    name: ClassVar[str] = "cowork"

    def __init__(self, roots: Iterable[str | Path] | None = None) -> None:
        selected = windows_data_roots() if roots is None else [Path(root) for root in roots]
        self._roots = tuple(sorted((root.resolve() for root in selected if root.is_dir()), key=lambda root: str(root).lower()))

    def root(self) -> Path:
        return self._roots[0] if self._roots else Path.home() / "AppData" / "Local" / "Claude-3p"

    @property
    def roots(self) -> tuple[Path, ...]:
        return self._roots

    def exists(self) -> bool:
        return bool(self._roots)

    def discover(self) -> list[Path]:
        files: list[Path] = []
        for root in self._roots:
            base = root / _AUDIT_DIR
            if not base.is_dir():
                continue
            for account in base.iterdir():
                if not account.is_dir():
                    continue
                for organization in account.iterdir():
                    if not organization.is_dir():
                        continue
                    for workspace in organization.iterdir():
                        audit = workspace / "audit.jsonl"
                        if workspace.name.startswith("local_") and audit.is_file():
                            files.append(audit)
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return files

    def key(self, path: Path) -> str:
        root = next(root for root in self._roots if path.is_relative_to(root))
        root_id = hashlib.sha256(str(root).encode()).hexdigest()[:12]
        return f"cowork/{root_id}/{path.relative_to(root).as_posix()}"

    def session_id(self, path: Path) -> str:
        return path.parent.name.removeprefix("local_")

    def read_records(self, path: Path) -> list[str]:
        try:
            with path.open(encoding="utf-8") as handle:
                return [record for raw in handle if (record := self._normalize(raw)) is not None]
        except (OSError, UnicodeDecodeError) as exc:
            raise TranscriptReadError(path, exc) from exc

    def classify(self, record: str) -> RecordKind:
        return classify_claude_record(record)

    @staticmethod
    def _normalize(raw: str) -> str | None:
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(entry, dict) or entry.get("type") not in ("user", "assistant") or entry.get("isReplay"):
            return None

        message = entry.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), (str, list)):
            return None
        normalized = {
            "type": entry["type"],
            "timestamp": entry.get("timestamp"),
            "message": {"role": message.get("role"), "content": message["content"]},
            "source": {"surface": "cowork", "container": "cowork_audit_jsonl"},
        }
        return json.dumps(normalized, ensure_ascii=False)
