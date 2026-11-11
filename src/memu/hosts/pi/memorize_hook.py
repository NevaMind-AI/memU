"""Detached pi memorization through the shared prepare/agent/commit pipeline."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import traceback
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from memu.hosts import hooks
from memu.hosts.bridging import Layout, self_sessions
from memu.hosts.hooks import admission, worker


@contextlib.contextmanager
def memorize_run(layout: Layout) -> Iterator[bool]:
    with admission.memorize_run(layout) as admitted:
        if not admitted:
            yield False
            return
        updates = {"PI_SESSION_ID": str(uuid4()), self_sessions.BRIDGING_RUN_ENV: "1"}
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
    # pi's Node stdin reader hangs on Windows TemporaryFile handles. Its native
    # prompt argument carries only the short job-directory instruction.
    worker.stream_agent([*argv, prompt], layout, "", timeout, env=dict(os.environ), stdin=subprocess.DEVNULL)


def launch_background(args: argparse.Namespace, event: dict[str, Any]) -> Path:
    session_file = Path(event["session_file"]).expanduser().resolve(strict=True)
    if not session_file.is_file() or session_file.suffix != ".jsonl":
        raise ValueError("Expected a persisted pi session file")  # noqa: TRY003
    agent = shutil.which("pi")
    if not agent:
        raise FileNotFoundError("pi is not on PATH")  # noqa: TRY003
    layout = Layout.default("pi", args.base_dir)
    layout.base.mkdir(parents=True, exist_ok=True)
    log_path = worker.new_log_path(layout.base).resolve()
    argv = [
        sys.executable,
        "-u",
        "-m",
        "memu.hosts.pi.memorize_hook",
        "--base-dir",
        str(layout.base.resolve()),
        "--session-dir",
        str(session_file.parent),
        "--agent",
        agent,
        "--log-path",
        str(log_path),
    ]
    for name in ("provider", "model"):
        value = event.get(name)
        if isinstance(value, str) and value.strip():
            argv.extend([f"--{name}", value])
    subprocess.Popen(  # noqa: S603
        argv,
        cwd=layout.base,
        env=dict(os.environ),
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
        if not isinstance(event, dict) or event.get("hook_event_name") != "agent_settled":
            raise ValueError("Expected an agent_settled object")  # noqa: TRY003, TRY301
        if os.environ.get(self_sessions.BRIDGING_RUN_ENV, "").strip() or not event.get("session_file"):
            print("{}")
            return 0
        if not isinstance(event["session_file"], str):
            raise TypeError("Expected session_file to be a path string")  # noqa: TRY003, TRY301
        log_path = launch_background(args, event)
    except (OSError, ValueError, TypeError) as exc:
        print(f"memU memorize hook failed: {exc}", file=sys.stderr)
        print("{}")
        return 1
    print(json.dumps({"log_path": str(log_path)}))
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("memorize-hook", help="Start background memory processing after a pi user turn settles")
    parser.add_argument("--base-dir", default="~/.memu/hosts/pi")
    parser.set_defaults(handler=_cmd_memorize_hook)


def main() -> int:
    from memu.hosts.host_cli import run
    from memu.hosts.pi.cli import SPEC

    parser = argparse.ArgumentParser()
    for name in ("base-dir", "session-dir", "agent", "log-path"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--provider")
    parser.add_argument("--model")
    args = parser.parse_args()
    if SPEC.hook is None:
        raise RuntimeError("pi memory hook is not configured")  # noqa: TRY003
    argv = list(SPEC.hook.agent.argv)
    for name in ("provider", "model"):
        if value := getattr(args, name):
            argv.extend([f"--{name}", value])
    spec = replace(SPEC, hook=replace(SPEC.hook, agent=hooks.HeadlessAgent(tuple(argv))))
    code = 1
    with (
        Path(args.log_path).open("a", encoding="utf-8", buffering=1) as log,
        contextlib.redirect_stdout(log),
        contextlib.redirect_stderr(log),
    ):
        print(f"=== WORKER pi pid={os.getpid()} ===", flush=True)
        try:
            code = run(
                spec,
                ["hook-run", "--base-dir", args.base_dir, "--session-dir", args.session_dir, "--agent", args.agent],
            )
        except Exception:
            traceback.print_exc()
        if code:
            print("=== MEMORIZE status=failed ===", flush=True)
        print(f"=== FINISHED pi exit={code} ===", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
