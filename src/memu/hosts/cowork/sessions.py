"""Claude Cowork audit logs stored by Claude Desktop."""

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
_ROOTS_ENV = "MEMU_COWORK_ROOTS"


def _existing_roots(candidates: Iterable[str | Path]) -> list[Path]:
    """Resolve, deduplicate, and sort existing Claude Desktop data roots."""
    roots: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = Path(candidate).expanduser().resolve()
        except OSError:
            continue
        if resolved.is_dir():
            roots.add(resolved)
    return sorted(roots, key=lambda root: str(root).lower())


def _override_roots(value: str) -> list[Path]:
    """Resolve a declared root list strictly so staging typos cannot fail silently."""
    candidates = [root.strip() for root in value.split(os.pathsep) if root.strip()]
    roots = _existing_roots(candidates)
    missing = []
    for candidate in candidates:
        try:
            resolved = Path(candidate).expanduser().resolve()
        except OSError:
            missing.append(candidate)
            continue
        if not resolved.is_dir():
            missing.append(candidate)
    if missing:
        msg = f"{_ROOTS_ENV} entries are not directories: {', '.join(missing)}"
        raise ValueError(msg)
    return roots


def windows_data_roots() -> list[Path]:
    """Return known Claude Desktop data roots that exist on this Windows install."""
    home = Path.home()
    appdata_value = os.environ.get("APPDATA", "").strip()
    local_appdata_value = os.environ.get("LOCALAPPDATA", "").strip()
    appdata = Path(appdata_value) if appdata_value else home / "AppData" / "Roaming"
    local_appdata = Path(local_appdata_value) if local_appdata_value else home / "AppData" / "Local"
    return _existing_roots([
        appdata / "Claude",
        local_appdata / "Claude-3p",
        *local_appdata.glob("Packages/Claude_*/LocalCache/Roaming/Claude"),
    ])


def macos_data_roots() -> list[Path]:
    """Return conventional Claude Desktop data roots that exist on this Mac."""
    support = Path.home() / "Library" / "Application Support"
    return _existing_roots([support / "Claude", support / "Claude-3p"])


def linux_data_roots() -> list[Path]:
    """Return conventional Claude Desktop data roots that exist on this Linux host."""
    config_home_value = os.environ.get("XDG_CONFIG_HOME", "").strip()
    config_home = Path(config_home_value) if config_home_value else Path.home() / ".config"
    return _existing_roots([config_home / "Claude", config_home / "Claude-3p"])


def platform_data_roots() -> list[Path]:
    """Return existing Cowork data roots for this platform, or an explicit override."""
    if _ROOTS_ENV in os.environ:
        return _override_roots(os.environ[_ROOTS_ENV])
    if sys.platform == "win32":
        return windows_data_roots()
    if sys.platform == "darwin":
        return macos_data_roots()
    if sys.platform.startswith("linux"):
        return linux_data_roots()
    return []


def _default_root() -> Path:
    """Return this platform's conventional data root for diagnostics."""
    if sys.platform == "win32":
        appdata_value = os.environ.get("APPDATA", "").strip()
        appdata = Path(appdata_value) if appdata_value else Path.home() / "AppData" / "Roaming"
        return appdata / "Claude"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude"
    if sys.platform.startswith("linux"):
        config_home_value = os.environ.get("XDG_CONFIG_HOME", "").strip()
        config_home = Path(config_home_value) if config_home_value else Path.home() / ".config"
        return config_home / "Claude"
    return Path.home()


class CoworkTranscriptSource(TranscriptSource):
    """Read one user-visible Cowork workspace per ``local_*/audit.jsonl`` file."""

    name: ClassVar[str] = "cowork"

    def __init__(self, roots: Iterable[str | Path] | None = None) -> None:
        selected = platform_data_roots() if roots is None else roots
        self._roots = tuple(_existing_roots(selected))

    def root(self) -> Path:
        return self._roots[0] if self._roots else _default_root()

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
            "timestamp": entry.get("timestamp") or entry.get("_audit_timestamp"),
            "message": {"role": message.get("role"), "content": message["content"]},
            "source": {"surface": "cowork", "container": "cowork_audit_jsonl"},
        }
        return json.dumps(normalized, ensure_ascii=False)
