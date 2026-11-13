"""Remove managed Hermes instructions and migrate legacy memU plugins via CLI."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from memu.hosts import instruction
from memu.hosts.bridging.recall_files import _atomic_write_text
from memu.hosts.hermes.sessions import hermes_home
from memu.hosts.hooks.admission import workspace_lock

NAME = "memu-memory"
MARKER = "# memU managed Hermes plugin."


def home() -> Path:
    return hermes_home().resolve()


def target() -> Path:
    root = home() / "plugins"
    path = root / NAME
    if root.is_symlink() or path.is_symlink():
        raise ValueError("Refusing to modify a linked Hermes plugin location")  # noqa: TRY003
    if path.exists():
        if not path.is_dir():
            raise ValueError("Hermes plugin location is not a directory")  # noqa: TRY003
        for name in ("plugin.yaml", "__init__.py"):
            entry = path / name
            if entry.is_symlink() or (entry.exists() and not entry.read_text(encoding="utf-8").startswith(MARKER)):
                raise ValueError("Refusing to modify an unowned Hermes plugin")  # noqa: TRY003
        if not (path / "plugin.yaml").exists() or not (path / "__init__.py").exists():
            raise ValueError("Incomplete Hermes plugin; check ownership before retrying")  # noqa: TRY003
    return path


def command(*argv: str) -> str:
    executable = shutil.which("hermes")
    if not executable:
        raise FileNotFoundError("hermes is not on PATH")  # noqa: TRY003
    result = subprocess.run(  # noqa: S603
        [executable, *argv],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=dict(os.environ, HERMES_HOME=str(home()), PYTHONIOENCODING="utf-8"),
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Hermes command {argv[0]} failed")  # noqa: TRY003
    return result.stdout


def _owned_hook(entry: Any) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("command"), str):
        return False
    try:
        argv = shlex.split(entry["command"])
    except ValueError:
        return False
    offset = 2 if argv[1:2] == ["-I"] else 1
    return argv[offset : offset + 3] == ["-m", "memu.hosts.hermes.cli", "memorize-hook"]


def configure_memorize(base: Path | None) -> None:
    """Patch only our shell-hook entries; preserve unrelated hooks and consent."""
    hooks = json.loads(command("config", "get", "hooks", "--json"))
    if not isinstance(hooks, dict):
        raise TypeError("Hermes hooks configuration is not an object")  # noqa: TRY003
    entries = hooks.get("on_session_end", [])
    if not isinstance(entries, list):
        raise TypeError("Hermes on_session_end hooks must be a list")  # noqa: TRY003

    previous = [entry["command"] for entry in entries if _owned_hook(entry)]
    kept = [entry for entry in entries if not _owned_hook(entry)]
    hook_command = None
    if base is not None:
        hook_command = shlex.join([
            str(Path(sys.executable)).replace("\\", "/"),
            "-I",
            "-m",
            "memu.hosts.hermes.cli",
            "memorize-hook",
            "--base-dir",
            str(base.expanduser().resolve()).replace("\\", "/"),
        ])
        kept.append({"command": hook_command, "timeout": 10})
    if kept:
        hooks["on_session_end"] = kept
    else:
        hooks.pop("on_session_end", None)
    if kept:
        command("config", "set", "hooks.on_session_end", json.dumps(kept))
    else:
        command("config", "unset", "hooks.on_session_end")
    if json.loads(command("config", "get", "hooks", "--json")) != hooks:
        raise RuntimeError("Hermes shell hook configuration readback failed")  # noqa: TRY003
    allowlist = home() / "shell-hooks-allowlist.json"
    consent = json.loads(allowlist.read_text(encoding="utf-8")) if allowlist.exists() else {}
    approvals = consent.get("approvals", [])
    if not isinstance(approvals, list):
        raise TypeError("Hermes shell hook approvals must be a list")  # noqa: TRY003
    approvals = [
        item
        for item in approvals
        if not (isinstance(item, dict) and item.get("event") == "on_session_end" and item.get("command") in previous)
    ]
    if hook_command:
        approvals.append({"event": "on_session_end", "command": hook_command})
    consent["approvals"] = approvals
    _atomic_write_text(allowlist, json.dumps(consent, indent=2) + "\n")
    if hook_command and hook_command not in command("hooks", "list"):
        raise RuntimeError("Hermes did not recognize the installed memorize shell hook")  # noqa: TRY003


def remove_legacy_plugin() -> int:
    destination = target()
    if not destination.exists():
        return 0
    if any(entry.name not in {"plugin.yaml", "__init__.py", "__pycache__"} for entry in destination.iterdir()):
        raise ValueError("Hermes memU plugin contains extra files; inspect before removal")  # noqa: TRY003
    cache = destination / "__pycache__"
    if cache.is_symlink() or (
        cache.exists()
        and any(
            entry.is_symlink()
            or not entry.is_file()
            or not entry.name.startswith("__init__.")
            or entry.suffix != ".pyc"
            for entry in cache.iterdir()
        )
    ):
        raise ValueError("Hermes memU plugin cache contains unowned files")  # noqa: TRY003
    command("plugins", "remove", NAME)
    if destination.exists():
        raise RuntimeError("Hermes plugin removal did not remove the managed directory")  # noqa: TRY003
    return 1


async def remove(args: argparse.Namespace) -> int:
    lock = home() / ".memu-hooks-lock"
    lock.mkdir(parents=True, exist_ok=True)
    with workspace_lock(lock) as acquired:
        if not acquired:
            print("Another Hermes installation update is running", file=sys.stderr)
            return 2
        if platform.system() == "Windows":
            from memu.hosts.hermes.install import _command

            with contextlib.redirect_stdout(sys.stderr):
                code = await _command(["schedule", "uninstall", "--base-dir", str(args.base_dir)])
            if code:
                return 1
        configure_memorize(None)
        removed = remove_legacy_plugin()
        instruction.remove(home() / "SOUL.md", "memu-hermes")
        instruction.remove_skill(home() / "skills")
    notice = (
        "Start a fresh Hermes session to refresh SOUL.md; restart running Hermes processes after legacy plugin removal."
    )
    if args.json:
        print(json.dumps({"status": "passed", "removed": removed, "notice": notice}))
    else:
        print(f"Removed memU instructions and {removed} legacy plugin(s). {notice}")
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("uninstall", help="Remove managed Hermes instructions and legacy plugin; preserve memory")
    from memu.hosts.hermes.cli import SPEC

    parser.add_argument("--base-dir", default=SPEC.default_base_dir, help="memU working directory for legacy tasks")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=remove)
