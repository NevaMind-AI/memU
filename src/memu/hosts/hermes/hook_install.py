"""Install only memU-owned Hermes plugin files; delegate activation to Hermes."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from memu.hosts.bridging.recall_files import _atomic_write_text
from memu.hosts.hermes.sessions import hermes_home
from memu.hosts.hooks.admission import workspace_lock

NAME = "memu-memory"
MIN_VERSION = (0, 23, 1)
INJECTION_KEY = f"plugins.entries.{NAME}.allow_gateway_injection"
MARKER = "# memU managed Hermes plugin."
MANIFEST = f"""{MARKER}
name: {NAME}
version: "0.2.0"
requires_hermes: ">=0.23.1"
description: memU asynchronous retrieval and background memory
provides_hooks:
  - pre_llm_call
  - on_session_end
  - on_session_finalize
"""


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


def plugin_content(base: Path) -> str:
    template = files("memu.hosts.hermes").joinpath("plugin.py").read_text(encoding="utf-8")
    return template.replace('"__MEMU_PYTHON__"', repr(sys.executable)).replace(
        '"__MEMU_BASE_DIR__"', repr(str(base.expanduser().resolve()))
    )


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


def check_version() -> str:
    output = command("--version")
    match = re.search(r"(?m)^Hermes Agent v(\d+)\.(\d+)\.(\d+)(-[\w.-]+)?", output)
    if match:
        version = tuple(int(match[index]) for index in (1, 2, 3))
        if MIN_VERSION <= version < (2000, 0, 0) and not (version == MIN_VERSION and match[4]):
            return ".".join(match[index] for index in (1, 2, 3))
    raise ValueError("Hermes >= 0.23.1 is required for asynchronous context injection; update Hermes and retry")  # noqa: TRY003


def install(base: Path) -> Path:
    destination = target()
    destination.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(destination / "__init__.py", plugin_content(base))
    _atomic_write_text(destination / "plugin.yaml", MANIFEST)
    command("config", "set", INJECTION_KEY, "true")
    if json.loads(command("config", "get", INJECTION_KEY, "--json")) is not True:
        raise RuntimeError("Hermes did not confirm the memU context injection grant")  # noqa: TRY003
    command("plugins", "enable", NAME)
    return destination


async def remove(args: argparse.Namespace) -> int:
    lock = home() / ".memu-hooks-lock"
    lock.mkdir(parents=True, exist_ok=True)
    with workspace_lock(lock) as acquired:
        if not acquired:
            print("Another Hermes plugin update is running", file=sys.stderr)
            return 2
        destination = target()
        if platform.system() == "Windows":
            from memu.hosts.hermes.install import _command

            with contextlib.redirect_stdout(sys.stderr):
                code = await _command(["schedule", "uninstall", "--base-dir", str(args.base_dir)])
            if code:
                return 1
        removed = int(destination.exists())
        if removed:
            # Hermes owns config bookkeeping and unloading. Refuse unknown user files
            # before asking its native remove command to remove the plugin directory.
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
    notice = "Restart Hermes to unload the memU plugin. An active memory worker may finish its current pass."
    if args.json:
        print(json.dumps({"status": "passed", "removed": removed, "notice": notice}))
    else:
        print(f"Removed {removed} memU plugin(s). {notice}")
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("uninstall", help="Remove memU's Hermes plugin; preserve settings, sessions and memory")
    from memu.hosts.hermes.cli import SPEC

    parser.add_argument("--base-dir", default=SPEC.default_base_dir, help="memU working directory for legacy tasks")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=remove)
