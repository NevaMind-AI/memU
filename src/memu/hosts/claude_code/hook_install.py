"""Ownership-checked edits to Claude's user hook settings."""

from __future__ import annotations

import json
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

from memu.hosts.codex.prompt_hook_install import _atomic_write

SUBCOMMANDS = ("prompt-hook", "memorize-hook")


def home() -> Path:
    return Path.home() / ".claude"


def read() -> tuple[Path, bytes | None, dict[str, Any]]:
    path = home() / "settings.json"
    if path.is_symlink():
        raise ValueError("Claude settings.json is a symlink; inspect its ownership before installation")  # noqa: TRY003
    original = path.read_bytes() if path.exists() else None
    data = json.loads(original.decode("utf-8-sig")) if original is not None else {}
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise TypeError("Claude settings must be an object with a hooks object")  # noqa: TRY003
    for groups in data.get("hooks", {}).values():
        if not isinstance(groups, list) or any(
            not isinstance(group, dict)
            or not isinstance(group.get("hooks"), list)
            or any(not isinstance(hook, dict) for hook in group["hooks"])
            for group in groups
        ):
            raise ValueError("Invalid Claude hook groups; settings were not changed")  # noqa: TRY003
    return path, original, data


def owns(hook: dict[str, Any], subcommand: str) -> bool:  # noqa: C901 — validate legacy and exec-form arguments
    if hook.get("type") != "command" or not isinstance(hook.get("command"), str):
        return False
    command = hook["command"]
    args = hook.get("args")
    if args is None:
        try:
            words = shlex.split(command, posix=True)
        except ValueError:
            return False
        if words and words[0] == "&":
            words.pop(0)
        if len(words) < 2:
            return False
        command, args = words[0], words[1:]
    if not isinstance(args, list) or not args or args[0] != subcommand:
        return False
    if command.replace("\\", "/").rsplit("/", 1)[-1].casefold() not in {"memu-claude-code", "memu-claude-code.exe"}:
        return False
    rest = args[1:]
    while rest:
        if rest[0] == "--rewake" and subcommand == "prompt-hook":
            rest = rest[1:]
            continue
        if len(rest) < 2 or rest[0] not in {"--base-dir", "--session-dir", "--agent"} or not isinstance(rest[1], str):
            return False
        rest = rest[2:]
    return True


def definitions(base: Path) -> list[dict[str, Any]]:
    executable = str(Path(shutil.which(sys.argv[0]) or sys.argv[0]).resolve())
    return [
        {
            "type": "command",
            "command": executable,
            "args": [subcommand, "--base-dir", str(base)]
            + (["--session-dir", str(home() / "projects")] if subcommand == "memorize-hook" else ["--rewake"]),
            "timeout": 45 if subcommand == "prompt-hook" else 10,
            **({"asyncRewake": True} if subcommand == "prompt-hook" else {}),
        }
        for subcommand in SUBCOMMANDS
    ]


def _write(path: Path, original: bytes | None, data: dict[str, Any]) -> None:
    content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if content == original:
        return
    current = path.read_bytes() if path.exists() else None
    if current != original:
        raise RuntimeError("Claude settings changed during installation; rerun instead of overwriting")  # noqa: TRY003
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_name("settings.json.memu-backup")
    if backup.is_symlink():
        raise ValueError("Claude settings backup is a symlink; inspect ownership before updating")  # noqa: TRY003
    if original is not None and not backup.exists():
        backup.write_bytes(original)
    _atomic_write(path, content)
    if path.read_bytes() != content:
        raise RuntimeError("Claude settings read-back failed")  # noqa: TRY003


def install(base: Path) -> None:
    path, original, data = read()
    if data.get("disableAllHooks") is True or data.get("allowManagedHooksOnly") is True:
        raise ValueError("Claude settings disable user hooks; enable them before installing memU")  # noqa: TRY003
    groups = data.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    for definition, subcommand in zip(definitions(base), SUBCOMMANDS, strict=True):
        matching = [(group, hook) for group in groups for hook in group["hooks"] if owns(hook, subcommand)]
        # A matcher could restrict delivery; register one unconditional group for each owned hook.
        for group, hook in matching:
            group["hooks"].remove(hook)
            if not group["hooks"]:
                groups.remove(group)
        groups.append({"hooks": [definition]})
    _write(path, original, data)
    if problems():
        raise RuntimeError("Claude hook definition verification failed")  # noqa: TRY003


def uninstall() -> int:
    path, original, data = read()
    count = 0
    for groups in data.get("hooks", {}).values():
        for group in groups[:]:
            kept = [hook for hook in group["hooks"] if not any(owns(hook, name) for name in SUBCOMMANDS)]
            removed = len(group["hooks"]) - len(kept)
            count += removed
            if removed:
                group["hooks"] = kept
                if not kept:
                    groups.remove(group)
    if count:
        _write(path, original, data)
    return count


def problems() -> list[str]:
    _, _, data = read()
    issues = []
    if data.get("disableAllHooks") is True or data.get("allowManagedHooksOnly") is True:
        issues.append("User hooks are disabled by Claude settings")
    groups = data.get("hooks", {}).get("UserPromptSubmit", [])
    for subcommand in SUBCOMMANDS:
        matches = [(group, hook) for group in groups for hook in group["hooks"] if owns(hook, subcommand)]
        if not matches:
            issues.append(f"{subcommand}: missing")
        elif len(matches) != 1:
            issues.append(f"{subcommand}: duplicate definitions; update recommended")
        else:
            group, hook = matches[0]
            if (
                group.get("matcher")
                or "args" not in hook
                or "--agent" in hook["args"]
                or hook.get("async", False)
                or hook.get("asyncRewake", False) != (subcommand == "prompt-hook")
                or ("--rewake" in hook["args"]) != (subcommand == "prompt-hook")
                or hook.get("timeout") != (45 if subcommand == "prompt-hook" else 10)
            ):
                issues.append(f"{subcommand}: outdated definition; update recommended")
            elif not Path(hook["command"]).is_absolute() or not Path(hook["command"]).is_file():
                issues.append(f"{subcommand}: memU executable missing; reinstall memu-cli and run install")
    return issues
