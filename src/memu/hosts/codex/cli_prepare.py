"""Prepare the standalone Codex executable without changing memU integration."""

# Installer messages use Chinese punctuation.
# ruff: noqa: RUF001

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from memu import trust
from memu.hosts.codex.install_language import text


def _installation_directory() -> Path:
    if directory := os.environ.get("CODEX_INSTALL_DIR"):
        return Path(directory).expanduser()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise RuntimeError("LOCALAPPDATA is unavailable; supply --codex or CODEX_INSTALL_DIR")  # noqa: TRY003
        return Path(local) / "Programs/OpenAI/Codex/bin"
    return Path.home() / ".local/bin"


def _desktop_binary(path: Path) -> bool:
    """Desktop bundles are not standalone CLI installations."""
    normalized = str(path).replace("\\", "/").casefold()
    parts = normalized.split("/")
    local = os.environ.get("LOCALAPPDATA")
    desktop = str(Path(local) / "OpenAI/Codex").replace("\\", "/").casefold() if local else ""
    return (
        bool(desktop and normalized.startswith(desktop + "/"))
        or "/openai/codex/bin/" in normalized
        or "/codex.app/contents/" in normalized
        or any(part.startswith("openai.codex_") for part in parts)
    )


def _discover(executable: str | None) -> Path | None:
    if executable is not None:
        selected = Path(executable).expanduser()
        found = str(selected) if selected.is_file() else shutil.which(executable)
        if found is None:
            raise FileNotFoundError("The selected Codex executable does not exist")  # noqa: TRY003
        selected = Path(found).resolve()
        if _desktop_binary(selected):
            raise ValueError("Select a standalone Codex CLI, not the executable bundled with Codex Desktop")  # noqa: TRY003
        return selected
    name = "codex.exe" if sys.platform == "win32" else "codex"
    candidate = _installation_directory() / name
    if candidate.is_file() and not _desktop_binary(candidate.resolve()):
        return candidate.resolve()
    found = shutil.which("codex")
    if found and not _desktop_binary(Path(found).resolve()):
        return Path(found).resolve()
    # Desktop can prepend its own binary directory to PATH; search remaining entries.
    if found:
        paths = [entry for entry in os.get_exec_path() if not _desktop_binary((Path(entry) / name).resolve())]
        alternative = shutil.which("codex", path=os.pathsep.join(paths))
        if alternative and not _desktop_binary(Path(alternative).resolve()):
            return Path(alternative).resolve()
    return None


def find_executable() -> Path:
    """Find the current standalone CLI, resolving Windows npm wrappers for both hooks."""
    executable = _discover(None)
    if executable is None:
        raise FileNotFoundError("Standalone Codex CLI unavailable")  # noqa: TRY003
    if sys.platform == "win32" and executable.suffix.lower() != ".exe":
        candidates = list(
            executable.parent.glob(
                "node_modules/@openai/codex/node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"
            )
        )
        if len(candidates) != 1:
            raise FileNotFoundError("Native Codex executable unavailable")  # noqa: TRY003
        executable = candidates[0]
    return executable


def _install() -> None:
    windows = sys.platform == "win32"
    shell = shutil.which("powershell.exe" if windows else "sh")
    if shell is None:
        raise FileNotFoundError("The official Codex installer requires PowerShell on Windows or sh on Unix")  # noqa: TRY003
    extension = "ps1" if windows else "sh"
    url = f"https://chatgpt.com/codex/install.{extension}"
    print(text("📥 正在下载官方 Codex 安装器：{url}", url=url), file=sys.stderr, flush=True)
    with tempfile.TemporaryDirectory(prefix="memu-codex-install-") as directory:
        script = Path(directory) / f"install.{extension}"
        request = urllib.request.Request(url, headers={"User-Agent": "memu-cli"})  # noqa: S310
        with urllib.request.urlopen(request, timeout=30, **trust.urlopen_kwargs()) as response:  # noqa: S310
            data = response.read(1024 * 1024 + 1)
        if not data or len(data) > 1024 * 1024:
            raise ValueError("The Codex installer download is empty or exceeds 1 MiB")  # noqa: TRY003
        script.write_bytes(data)
        argv = (
            [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)]
            if windows
            else [shell, str(script)]
        )
        print(text("📦 正在运行官方安装器，下载和安装可能需要几分钟……"), file=sys.stderr, flush=True)
        # Keep installer diagnostics separate from the command's optional JSON result.
        subprocess.run(  # noqa: S603
            argv,
            stdin=subprocess.DEVNULL,
            stdout=sys.stderr,
            stderr=sys.stderr,
            env={**os.environ, "CODEX_NON_INTERACTIVE": "1"},
            timeout=300,
            check=True,
        )


def _probe(path: Path) -> dict[str, Any]:
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
        return {"status": "failed", "reason": "startup_failed", "detail": "Codex --version did not succeed."}
    return {"status": "passed", "version": version}


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
        result.update(_probe(path))
    except urllib.error.HTTPError as exc:
        result.update(
            status="failed",
            reason="download_http_error",
            http_status=exc.code,
            detail=f"Official Codex installer download failed: HTTP {exc.code} ({exc.reason}).",
        )
    except urllib.error.URLError as exc:
        result.update(
            status="failed",
            reason="download_connection_error",
            detail=f"Could not connect to the official Codex installer: {exc.reason}.",
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            status="failed",
            reason="timeout",
            timeout_seconds=exc.timeout,
            detail=f"Codex command timed out after {exc.timeout} seconds.",
        )
    except subprocess.CalledProcessError as exc:
        result.update(
            status="failed",
            reason="installer_exit",
            exit_code=exc.returncode,
            detail=f"Official Codex installer exited with code {exc.returncode}; see its output above.",
        )
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
