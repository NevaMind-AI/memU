"""Standalone Claude Code discovery, official installation and authentication status."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from memu import trust


def _desktop_binary(path: Path) -> bool:
    value = str(path).replace("\\", "/").casefold()
    return (
        "/claude.app/contents/" in value
        or "/anthropicclaude_" in value
        or "/appdata/local/anthropicclaude/" in value
        or "/appdata/local/claude/" in value
    )


def find_executable(selected: str | None = None) -> Path:
    """Prefer the native install, then standalone PATH entries; never scan the disk."""
    if selected:
        candidate = Path(selected).expanduser()
        path = candidate if candidate.is_file() else Path(shutil.which(selected) or selected)
        if not path.is_file() or _desktop_binary(path.resolve()):
            raise FileNotFoundError("Select an existing standalone Claude CLI, not a Desktop bundle")  # noqa: TRY003
        return path.resolve()
    name = "claude.exe" if sys.platform == "win32" else "claude"
    native = Path.home() / ".local/bin" / name
    if native.is_file() and not _desktop_binary(native.resolve()):
        return native.resolve()
    for directory in os.get_exec_path():
        found = shutil.which("claude", path=directory)
        if found and not _desktop_binary(Path(found).resolve()):
            return Path(found).resolve()
    raise FileNotFoundError("Standalone Claude CLI unavailable; run memu-claude-code install --install-missing")  # noqa: TRY003


def _install() -> None:
    windows = sys.platform == "win32"
    shell = shutil.which("powershell.exe" if windows else "bash")
    if shell is None:
        raise FileNotFoundError("The official Claude installer requires PowerShell on Windows or bash on Unix")  # noqa: TRY003
    suffix = "ps1" if windows else "sh"
    url = f"https://claude.ai/install.{suffix}"
    print(f"Downloading official Claude installer: {url}", file=sys.stderr, flush=True)
    with tempfile.TemporaryDirectory(prefix="memu-claude-install-") as directory:
        script = Path(directory) / f"install.{suffix}"
        request = urllib.request.Request(url, headers={"User-Agent": "memu-cli"})  # noqa: S310
        with urllib.request.urlopen(request, timeout=30, **trust.urlopen_kwargs()) as response:  # noqa: S310
            data = response.read(1024 * 1024 + 1)
        if not data or len(data) > 1024 * 1024:
            raise ValueError("Invalid official installer download size")  # noqa: TRY003
        script.write_bytes(data)
        argv = (
            [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)]
            if windows
            else [shell, str(script)]
        )
        subprocess.run(  # noqa: S603
            argv, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr, timeout=300, check=True
        )


def prepare(selected: str | None = None, *, install_missing: bool = False) -> Path:
    try:
        executable = find_executable(selected)
    except FileNotFoundError:
        if selected or not install_missing:
            raise
        _install()
        executable = find_executable()
    result = subprocess.run(  # noqa: S603
        [str(executable), "--version"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=20,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not re.fullmatch(r"\d+\.\d+\.\d+[^\r\n]* \(Claude Code\)", result.stdout.strip()):
        raise ValueError("Claude --version did not report a Claude Code version")  # noqa: TRY003
    return executable


def auth_status(executable: Path) -> bool:
    """Read CLI authentication status without a model turn or exposing credentials."""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    result = subprocess.run(  # noqa: S603
        [str(executable), "auth", "status", "--json"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env=env,
        timeout=20,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    value: Any = json.loads(result.stdout)
    return result.returncode == 0 and isinstance(value, dict) and value.get("loggedIn") is True
