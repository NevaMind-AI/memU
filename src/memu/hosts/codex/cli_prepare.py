"""Prepare the standalone Codex executable without changing memU integration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from memu import trust


def _installation_directory() -> Path:
    if directory := os.environ.get("CODEX_INSTALL_DIR"):
        return Path(directory).expanduser()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise RuntimeError("LOCALAPPDATA is unavailable; supply --codex or CODEX_INSTALL_DIR")  # noqa: TRY003
        return Path(local) / "Programs/OpenAI/Codex/bin"
    return Path.home() / ".local/bin"


def _discover(executable: str | None) -> Path | None:
    if executable is not None:
        selected = Path(executable).expanduser()
        found = str(selected) if selected.is_file() else shutil.which(executable)
        if found is None:
            raise FileNotFoundError("The selected Codex executable does not exist")  # noqa: TRY003
        return Path(found).resolve()
    if found := shutil.which("codex"):
        return Path(found).resolve()
    name = "codex.exe" if sys.platform == "win32" else "codex"
    candidate = _installation_directory() / name
    return candidate.resolve() if candidate.is_file() else None


def _install() -> None:
    windows = sys.platform == "win32"
    shell = shutil.which("powershell.exe" if windows else "sh")
    if shell is None:
        raise FileNotFoundError("The official Codex installer requires PowerShell on Windows or sh on Unix")  # noqa: TRY003
    extension = "ps1" if windows else "sh"
    url = f"https://chatgpt.com/codex/install.{extension}"
    with tempfile.TemporaryDirectory(prefix="memu-codex-install-") as directory:
        script = Path(directory) / f"install.{extension}"
        with urllib.request.urlopen(url, timeout=30, **trust.urlopen_kwargs()) as response:  # noqa: S310
            data = response.read(1024 * 1024 + 1)
        if not data or len(data) > 1024 * 1024:
            raise ValueError("The Codex installer download is empty or exceeds 1 MiB")  # noqa: TRY003
        script.write_bytes(data)
        argv = (
            [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)]
            if windows
            else [shell, str(script)]
        )
        # Keep installer diagnostics separate from the command's optional JSON result.
        subprocess.run(  # noqa: S603
            argv, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr, timeout=300, check=True
        )


def prepare(executable: str | None = None, *, install_missing: bool = False) -> dict[str, Any]:
    """Discover, optionally install, then verify startup; authentication is separate."""
    result: dict[str, Any] = {"stage": "host_executable", "status": "blocked", "executable": None}
    try:
        path = _discover(executable)
        if path is None:
            if not install_missing:
                result.update(
                    reason="missing",
                    detail="Codex CLI was not found. Re-run with --install-missing to use the official installer.",
                )
                return result
            _install()
            path = _discover(None)
            if path is None:
                result.update(reason="install_incomplete", detail="Installer finished but Codex CLI was not found.")
                return result
        result["executable"] = str(path)
        probe = subprocess.run(  # noqa: S603
            [str(path), "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        version = probe.stdout.strip()
        if probe.returncode or not version.startswith("codex-cli "):
            result.update(status="failed", reason="startup_failed", detail="Codex --version did not succeed.")
            return result
        result.update(status="passed", version=version)
    except FileNotFoundError as exc:
        result.update(reason="not_found", detail=str(exc))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        result.update(status="failed", reason="preparation_failed", detail=str(exc))
    return result


def register(sub: Any) -> None:
    parser = sub.add_parser("prepare-cli", help="Find or install Codex and verify startup (not authentication)")
    parser.add_argument("--codex", default=None, help="Selected Codex executable; never replaced automatically")
    parser.add_argument(
        "--install-missing", action="store_true", help="Allow the official installer if Codex is absent"
    )
    parser.add_argument("--json", action="store_true", help="Print a structured preparation result")

    async def handler(args: argparse.Namespace) -> int:
        result = prepare(args.codex, install_missing=args.install_missing)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        elif result["status"] == "passed":
            print(f"Codex executable ready: {result['executable']} ({result['version']}).")
            print("Authentication, background execution and memU integration have not been checked.")
        else:
            print(f"Codex preparation {result['status']}: {result['detail']}", file=sys.stderr)
        return {"passed": 0, "blocked": 2, "failed": 1}[result["status"]]

    parser.set_defaults(handler=handler)
