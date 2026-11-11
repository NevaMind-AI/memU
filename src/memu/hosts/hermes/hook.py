"""Hermes plugin subprocess entry points and detached memory worker."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4

from memu.env import LONG_QUERY_CHARS
from memu.hosts.bridging import Layout, self_sessions
from memu.hosts.hermes.query_extraction import select_query
from memu.hosts.hermes.sessions import hermes_home, state_db_path
from memu.hosts.hooks import worker
from memu.hosts.retrieval import QueryKind, render_context, retrieve


def stream_agent(argv: list[str], layout: Layout, prompt: str, timeout: int) -> None:
    worker.stream_agent(
        [*argv, "-z", prompt],
        layout,
        "",
        timeout,
        env=dict(os.environ, MEMU_BRIDGING_RUN="1", HERMES_HOME=str(hermes_home())),
        stdin=subprocess.DEVNULL,
    )


async def retrieve_context(base: Path, event: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    trace: dict[str, Any] = {"session_id": event.get("session_id"), "status": "started"}
    try:
        prompt = event.get("prompt")
        if not isinstance(prompt, str):
            raise TypeError("Expected a prompt string")  # noqa: TRY003, TRY301
        if not prompt.strip():
            trace["status"] = "input_skipped"
            return {"context": None}
        python = event.get("hermes_python")
        paths = event.get("hermes_sys_path")
        query = await asyncio.to_thread(
            select_query,
            prompt,
            trace,
            python=python if isinstance(python, str) else None,
            python_paths=paths if isinstance(paths, list) and all(isinstance(path, str) for path in paths) else None,
        )
        kind: QueryKind = (
            "extracted"
            if trace.get("query_source") == "extracted"
            else "long"
            if sum(not char.isspace() for char in prompt) >= LONG_QUERY_CHARS
            else "short"
        )
        trace.update(query=query, query_kind=kind, query_truncated=trace.get("query_source") == "prefix")
        memories = await asyncio.wait_for(retrieve(query, query_kind=kind), timeout=20)
        context = render_context(memories)
        trace.update(status="context_returned", retrieve_result=memories, additional_context=context)
    except Exception as exc:
        trace.update(status="failed", error_type=type(exc).__name__)
        raise
    else:
        return {"context": context}
    finally:
        trace["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        directory = base / "log/hooks/retrieve"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{uuid4()}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def launch_background(base: Path) -> Path:
    agent = shutil.which("hermes")
    if not agent:
        raise FileNotFoundError("hermes is not on PATH")  # noqa: TRY003
    layout = Layout.default("hermes", base)
    layout.base.mkdir(parents=True, exist_ok=True)
    log = worker.new_log_path(layout.base).resolve()
    subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-u",
            "-m",
            "memu.hosts.hermes.hook",
            "worker",
            "--base-dir",
            str(base),
            "--agent",
            agent,
            "--log-path",
            str(log),
        ],
        cwd=base,
        env=dict(os.environ, HERMES_HOME=str(hermes_home()), PYTHONIOENCODING="utf-8"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=sys.platform != "win32",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return log


def run_worker(args: argparse.Namespace) -> int:
    from memu.hosts.hermes.cli import SPEC
    from memu.hosts.host_cli import run

    layout = Layout.default("hermes", args.base_dir)
    with (
        Path(args.log_path).open("a", encoding="utf-8", buffering=1) as log,
        contextlib.redirect_stdout(log),
        contextlib.redirect_stderr(log),
    ):
        print(f"=== WORKER hermes pid={os.getpid()} ===", flush=True)
        code = 1
        try:
            code = run(
                SPEC,
                [
                    "hook-run",
                    "--base-dir",
                    str(layout.base),
                    "--session-dir",
                    str(state_db_path()),
                    "--agent",
                    args.agent,
                ],
            )
        except Exception:
            traceback.print_exc()
        print(f"=== FINISHED hermes exit={code} ===", flush=True)
        return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("retrieve", "memorize", "remember-self", "worker"))
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--agent")
    parser.add_argument("--log-path")
    args = parser.parse_args()
    args.base_dir = args.base_dir.expanduser().resolve()
    if args.action == "worker":
        if not args.agent or not args.log_path:
            parser.error("worker requires --agent and --log-path")
        return run_worker(args)
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise TypeError("Expected a Hermes hook event object")  # noqa: TRY003, TRY301
        if args.action == "retrieve":
            output = asyncio.run(retrieve_context(args.base_dir, event))
        elif args.action == "remember-self":
            session_id = event.get("session_id")
            if not isinstance(session_id, str) or not session_id:
                raise ValueError("Expected a session id")  # noqa: TRY003, TRY301
            self_sessions.remember(Layout.default("hermes", args.base_dir).self_sessions, session_id)
            output = {}
        else:
            output = {"log_path": str(launch_background(args.base_dir))}
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
        print("memU Hermes hook failed; check the hook logs", file=sys.stderr)
        return 1
    else:
        print(json.dumps(output, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    sys.exit(main())
