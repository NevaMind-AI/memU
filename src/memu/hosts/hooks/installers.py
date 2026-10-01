"""Registering ``memu-<host> hook`` in each host's own hook configuration.

Each installer edits exactly one entry in a file the user also owns, so the
rules are the same everywhere: leave every other hook alone, be idempotent, and
refuse — rather than guess — when the file is not something we can parse.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from memu.hosts.bridging import Layout


class HookConfigError(ValueError):
    """The host's hook configuration could not be read or safely edited."""

    @classmethod
    def unreadable(cls, path: Path, exc: Exception) -> HookConfigError:
        return cls(f"cannot parse {path} ({exc}); fix or edit it by hand, nothing was changed")

    @classmethod
    def unexpected_shape(cls, path: Path, what: str) -> HookConfigError:
        return cls(f"{path}: {what} is not in the expected shape; edit it by hand, nothing was changed")

    @classmethod
    def edit_failed(cls, path: Path) -> HookConfigError:
        return cls(f"could not edit the top-level `notify` in {path} safely; edit it by hand, nothing was changed")


class HookInstaller(Protocol):
    path: Path

    def install(self, argv: list[str], layout: Layout) -> bool:
        """Register ``argv`` as the hook. Returns whether anything changed."""

    def remove(self, binary: str, layout: Layout) -> bool:
        """Unregister any hook running ``<binary> hook``. Returns whether anything changed."""

    def installed(self, binary: str) -> bool: ...

    def forward(self, layout: Layout, payload: list[str]) -> None:
        """Pass the host's hook payload on to whatever hook ours displaced, if any."""


def _is_our_argv(argv: list[str], binary: str) -> bool:
    if len(argv) < 2 or argv[1] != "hook":
        return False
    name = Path(argv[0]).name
    return name in {binary, f"{binary}.exe"}


def _command_line(argv: list[str]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(argv)
    import shlex

    return shlex.join(argv)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".memu-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class ClaudeSettingsHook:
    """A ``SessionEnd`` command hook in Claude Code's ``settings.json``.

    ``SessionEnd`` rather than ``Stop``: it fires once per session, not once per
    reply, and anything a session that never ends cleanly leaves behind is picked
    up by the next run anyway — ``prepare`` scans every session from its cursor.
    """

    EVENT = "SessionEnd"

    def __init__(self, path: str | Path = "~/.claude/settings.json") -> None:
        self.path = Path(os.path.expanduser(str(path)))

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, json.JSONDecodeError) as exc:
            raise HookConfigError.unreadable(self.path, exc) from exc
        if not isinstance(data, dict):
            raise HookConfigError.unexpected_shape(self.path, "the top level")
        return data

    def _groups(self, data: dict[str, Any]) -> list[Any]:
        hooks = data.get("hooks", {})
        if not isinstance(hooks, dict):
            raise HookConfigError.unexpected_shape(self.path, "`hooks`")
        groups = hooks.get(self.EVENT, [])
        if not isinstance(groups, list):
            raise HookConfigError.unexpected_shape(self.path, f"`hooks.{self.EVENT}`")
        return groups

    @staticmethod
    def _is_ours(entry: Any, binary: str) -> bool:
        if not isinstance(entry, dict) or not isinstance(entry.get("command"), str):
            return False
        pattern = rf"(^|[\\/\"' ]){re.escape(binary)}(\.exe)?[\"']?\s+hook(\s|$)"
        return re.search(pattern, entry["command"]) is not None

    def installed(self, binary: str) -> bool:
        return any(
            self._is_ours(entry, binary)
            for group in self._groups(self._load())
            if isinstance(group, dict)
            for entry in group.get("hooks", [])
        )

    def install(self, argv: list[str], layout: Layout) -> bool:
        binary = Path(argv[0]).name.removesuffix(".exe")
        command = _command_line(argv)
        data = self._load()
        groups = self._groups(data)
        current = [
            entry
            for group in groups
            if isinstance(group, dict)
            for entry in group.get("hooks", [])
            if self._is_ours(entry, binary)
        ]
        if len(current) == 1 and current[0]["command"] == command:
            return False
        self._strip(groups, binary)
        groups.append({"hooks": [{"type": "command", "command": command}]})
        data.setdefault("hooks", {})[self.EVENT] = groups
        _atomic_write(self.path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return True

    def remove(self, binary: str, layout: Layout) -> bool:
        if not self.path.exists():
            return False
        data = self._load()
        groups = self._groups(data)
        if not self._strip(groups, binary):
            return False
        hooks = data["hooks"]
        if groups:
            hooks[self.EVENT] = groups
        else:
            hooks.pop(self.EVENT, None)
        if not hooks:
            data.pop("hooks")
        _atomic_write(self.path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return True

    def _strip(self, groups: list[Any], binary: str) -> bool:
        """Drop our entries in place, and any group they leave empty."""
        changed = False
        for group in list(groups):
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                continue
            kept = [entry for entry in group["hooks"] if not self._is_ours(entry, binary)]
            if len(kept) == len(group["hooks"]):
                continue
            changed = True
            if kept:
                group["hooks"] = kept
            else:
                groups.remove(group)
        return changed

    def forward(self, layout: Layout, payload: list[str]) -> None:
        return None


class CodexNotifyHook:
    """Codex's top-level ``notify`` program in ``config.toml``.

    Codex takes exactly one notify program and runs it after every agent turn,
    with a JSON payload as the last argument. A user who already has one (another
    tool's collector, a desktop notifier) keeps it: its argv is saved beside the
    working tree, ``hook`` forwards each payload to it, and ``remove`` restores it.
    """

    KEY = "notify"
    CHAIN_FILE = "codex-notify-chain.json"

    def __init__(self, path: str | Path = "~/.codex/config.toml") -> None:
        self.path = Path(os.path.expanduser(str(path)))

    def _text(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        except OSError as exc:
            raise HookConfigError.unreadable(self.path, exc) from exc

    def _notify(self, text: str) -> list[str] | None:
        try:
            value = tomllib.loads(text).get(self.KEY)
        except tomllib.TOMLDecodeError as exc:
            raise HookConfigError.unreadable(self.path, exc) from exc
        if value is None:
            return None
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise HookConfigError.unexpected_shape(self.path, "`notify`")
        return value

    def _chain_path(self, layout: Layout) -> Path:
        return layout.base / self.CHAIN_FILE

    def installed(self, binary: str) -> bool:
        current = self._notify(self._text())
        return current is not None and _is_our_argv(current, binary)

    def install(self, argv: list[str], layout: Layout) -> bool:
        binary = Path(argv[0]).name.removesuffix(".exe")
        text = self._text()
        current = self._notify(text)
        if current == argv:
            return False
        if current is not None and not _is_our_argv(current, binary):
            _atomic_write(self._chain_path(layout), json.dumps(current, indent=2) + "\n")
        _atomic_write(self.path, self._with_notify(text, argv))
        return True

    def remove(self, binary: str, layout: Layout) -> bool:
        text = self._text()
        current = self._notify(text)
        if current is None or not _is_our_argv(current, binary):
            return False
        chain = self._chain(layout)
        _atomic_write(self.path, self._with_notify(text, chain))
        self._chain_path(layout).unlink(missing_ok=True)
        return True

    def _chain(self, layout: Layout) -> list[str] | None:
        try:
            value = json.loads(self._chain_path(layout).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
            return value
        return None

    def forward(self, layout: Layout, payload: list[str]) -> None:
        chain = self._chain(layout)
        if chain is None:
            return
        subprocess.Popen(  # noqa: S603 - the user's own notify program, restored verbatim
            [*chain, *payload],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=sys.platform != "win32",
        )

    def _with_notify(self, text: str, value: list[str] | None) -> str:
        """``text`` with its top-level ``notify`` set to ``value`` (removed if ``None``).

        A line edit, not a re-serialization, so the rest of the user's file —
        comments, ordering, formatting — survives byte for byte. Top-level keys
        must precede the first table, so only that prefix is searched, and a new
        key is simply prepended. The result is re-parsed and checked before it
        is allowed anywhere near the disk.
        """
        header = re.search(r"(?m)^[ \t]*\[", text)
        prefix, rest = (text[: header.start()], text[header.start() :]) if header else (text, "")
        line = f"{self.KEY} = [{', '.join(json.dumps(item) for item in value)}]\n" if value is not None else ""
        existing = re.compile(rf"(?ms)^[ \t]*{self.KEY}[ \t]*=[ \t]*\[.*?\][ \t]*(#[^\n]*)?(\n|\Z)")
        if existing.search(prefix):
            prefix = existing.sub(lambda _: line, prefix, count=1)
        elif value is not None:
            prefix = line + prefix
        updated = prefix + rest
        try:
            if self._notify(updated) != value:
                raise HookConfigError.edit_failed(self.path)
        except HookConfigError as exc:
            raise HookConfigError.edit_failed(self.path) from exc
        return updated
