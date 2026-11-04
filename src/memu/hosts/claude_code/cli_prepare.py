"""Standalone Claude Code discovery, official installation and authentication status."""

# ruff: noqa: RUF001

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from memu.hosts import cli_install
from memu.hosts.install_language import text


def standalone_env() -> dict[str, str]:
    """Load standalone configuration without inheriting Desktop authentication/routing."""
    env = os.environ.copy()
    desktop = env.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("claude-desktop")
    for name in list(env):
        desktop_route = desktop and (
            name in {"ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"}
            or (name.startswith("ANTHROPIC_DEFAULT_") and name.endswith("_MODEL"))
        )
        if (
            desktop_route
            or name.startswith("CLAUDE_CODE_HOST_")
            or name
            in {
                "CLAUDECODE",
                "CLAUDE_CODE_CHILD_SESSION",
                "CLAUDE_CODE_SESSION_ID",
                "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST",
                "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH",
                "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH",
                "CLAUDE_CODE_OAUTH_SCOPES",
                "CLAUDE_CODE_ENTRYPOINT",
                "CLAUDE_CODE_EXECPATH",
                "CLAUDE_CODE_ATTRIBUTION_HEADER",
                "CLAUDE_CODE_DIAGNOSTICS_FILE",
                "CLAUDE_PID",
            }
        ):
            env.pop(name)
    env["CLAUDE_CONFIG_DIR"] = str(Path.home() / ".claude")
    return env


def _desktop_binary(path: Path) -> bool:
    value = str(path).replace("\\", "/").casefold()
    return (
        "/claude.app/contents/" in value
        or "/anthropicclaude_" in value
        or "/appdata/local/anthropicclaude/" in value
        or "/appdata/local/claude/" in value
        # Desktop data roots are stable across package versions and MSIX redirection.
        or re.search(r"/(?:claude|claude-3p)/claude-code(?:-vm)?/", value) is not None
        or "/.claude/remote/ccd-cli/" in value
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
    suffix = "ps1" if sys.platform == "win32" else "sh"
    cli_install.install("Claude", f"https://claude.ai/install.{suffix}", unix_shell="bash")


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


def _safe_response(message: str) -> str:
    """Remove configured credentials and endpoint URLs from child diagnostics."""
    values = dict(os.environ)
    try:
        settings = json.loads((Path.home() / ".claude/settings.json").read_text(encoding="utf-8-sig"))
        if isinstance(settings, dict) and isinstance(settings.get("env"), dict):
            values.update(settings["env"])
    except (OSError, ValueError):
        pass
    for name, value in values.items():
        if (
            isinstance(value, str)
            and value
            and any(key in name.upper() for key in ("KEY", "TOKEN", "SECRET", "PASSWORD", "URL"))
        ):
            message = message.replace(value, "[redacted]")
    message = re.sub(r"https?://[^\s<>\"]+", "[endpoint]", message)
    message = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", message)
    message = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", message)
    return message[:2000]


def verify_request(executable: Path) -> None:
    """Check a real headless request without tools, hooks or local session history."""
    started = time.monotonic()
    print(text("   → Reply OK. · 等待回复（最多 60 秒）"), flush=True)
    env = {**standalone_env(), "MEMU_CLAUDE_MEMORIZE": "1"}
    with tempfile.TemporaryDirectory(prefix="memu-claude-check-") as directory:
        result = subprocess.run(  # noqa: S603
            [
                str(executable),
                "-p",
                "Reply OK.",
                "--output-format",
                "json",
                "--no-session-persistence",
                "--tools",
                "",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--settings",
                '{"disableAllHooks":true}',
                "--system-prompt",
                "Reply briefly. Do not use tools.",
            ],
            cwd=directory,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    seconds = f"{time.monotonic() - started:.1f}"
    try:
        value = json.loads(result.stdout)
    except ValueError:
        diagnostic = _safe_response(result.stderr.strip() or result.stdout.strip())
        raise ValueError(text("Claude 未返回有效 JSON 回复。") + ("\n" + diagnostic if diagnostic else "")) from None
    response = value.get("result", "") if isinstance(value, dict) else ""
    if (
        result.returncode
        or not isinstance(value, dict)
        or value.get("is_error")
        or not isinstance(response, str)
        or not response.strip()
    ):
        diagnostic = _safe_response(
            response if isinstance(response, str) and response.strip() else result.stderr.strip()
        )
        raise ValueError(
            text("Claude 请求失败（退出码 {code}，{seconds} 秒）。", code=str(result.returncode), seconds=seconds)
            + ("\n" + diagnostic if diagnostic else text("没有收到有效回复。"))
        )
    print(text("   ← {reply} · {seconds} 秒", reply=_safe_response(response.strip()), seconds=seconds), flush=True)


def auth_status(executable: Path) -> bool:
    """Read CLI authentication status without a model turn or exposing credentials."""
    env = standalone_env()
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
