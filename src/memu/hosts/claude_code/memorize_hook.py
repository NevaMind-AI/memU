"""Detached Claude Submit memorization through the shared bridging pipeline."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

from memu.hosts.bridging import Layout, self_sessions
from memu.hosts.hooks import admission, worker

BACKGROUND_ENV = "MEMU_CLAUDE_MEMORIZE"
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"


@contextlib.contextmanager
def memorize_run(layout: Layout) -> Iterator[bool]:
    """Assign a fresh worker session only after lock/cooldown admission."""
    with admission.memorize_run(layout) as admitted:
        if not admitted:
            yield False
            return
        updates = {BACKGROUND_ENV: "1", SESSION_ENV: str(uuid4()), self_sessions.BRIDGING_RUN_ENV: "1"}
        previous = {key: os.environ.get(key) for key in updates}
        os.environ.update(updates)
        try:
            yield True
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def stream_agent(argv: list[str], layout: Layout, prompt: str, timeout: int) -> None:
    session_id = os.environ[SESSION_ENV]
    self_sessions.remember(layout.self_sessions, session_id)
    env = os.environ.copy()
    # A detached headless run is independent of the invoking Claude frontend.
    env.pop("CLAUDECODE", None)
    worker.stream_agent([*argv, "--session-id", session_id], layout, prompt, timeout, env=env)


def launch_background(args: argparse.Namespace) -> Path:
    layout = Layout.default("claude-code", args.base_dir)
    layout.base.mkdir(parents=True, exist_ok=True)
    log_path = worker.new_log_path(layout.base).resolve()
    env = os.environ.copy()
    env.pop(SESSION_ENV, None)
    env.pop("CLAUDECODE", None)
    subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-u",
            "-m",
            "memu.hosts.claude_code.memorize_hook",
            "--base-dir",
            str(layout.base.resolve()),
            "--session-dir",
            str(Path(args.session_dir).expanduser().resolve()),
            "--agent",
            args.agent,
            "--log-path",
            str(log_path),
        ],
        cwd=layout.base,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=sys.platform != "win32",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
    )
    return log_path


async def _cmd_memorize_hook(args: argparse.Namespace) -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get("hook_event_name") != "UserPromptSubmit":
            raise ValueError("expected a UserPromptSubmit object")  # noqa: TRY003, TRY301
        if os.environ.get(BACKGROUND_ENV) != "1":
            launch_background(args)
    except (OSError, ValueError, TypeError) as exc:
        print(f"memU memorize hook failed: {exc}", file=sys.stderr)
    print("{}")
    return 0


def register(sub: Any) -> None:
    from memu.hosts.claude_code.sessions import SESSION_DIR

    parser = sub.add_parser("memorize-hook", help="Start background memory processing on Claude prompt submission")
    parser.add_argument("--base-dir", default="~/.memu/hosts/claude-code")
    parser.add_argument("--session-dir", default=SESSION_DIR)
    parser.add_argument("--agent", required=True, help="Path to the Claude executable")
    parser.set_defaults(handler=_cmd_memorize_hook)


def main() -> int:
    """Internal worker entry point; stdout/stderr belong to one complete run log."""
    from memu.hosts.claude_code.cli import main as claude_main

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--log-path", required=True)
    args = parser.parse_args()
    code = 1
    with (
        Path(args.log_path).open("a", encoding="utf-8", buffering=1) as log,
        contextlib.redirect_stdout(log),
        contextlib.redirect_stderr(log),
    ):
        print(f"=== WORKER claude-code pid={os.getpid()} ===", flush=True)
        try:
            code = claude_main([
                "hook-run",
                "--base-dir",
                args.base_dir,
                "--session-dir",
                args.session_dir,
                "--agent",
                args.agent,
            ])
        except Exception:
            traceback.print_exc()
        if code:
            print("=== MEMORIZE status=failed ===", flush=True)
        print(f"=== FINISHED claude-code exit={code} ===", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
