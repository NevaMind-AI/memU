"""Run Hermes through its CLI for the shared bridging worker."""

from __future__ import annotations

import json
import os
import subprocess

from memu.hosts.bridging import Layout, self_sessions
from memu.hosts.hermes.sessions import hermes_home
from memu.hosts.hooks import worker


def stream_agent(argv: list[str], layout: Layout, prompt: str, timeout: int) -> None:
    registered: set[str] = set()

    def capture(line: str) -> None:
        # Hermes chat emits the assigned ID on stderr before submitting the turn;
        # stream-json also reports it in the terminal result. Both are CLI output.
        session_id: object
        if line.startswith("Session: "):
            session_id = line.removeprefix("Session: ").strip()
            if session_id and session_id not in registered:
                self_sessions.remember(layout.self_sessions, session_id)
                registered.add(session_id)
            return
        try:
            event = json.loads(line)
        except ValueError:
            return
        if not isinstance(event, dict) or event.get("type") not in {"system", "result"}:
            return
        session_id = event.get("session_id")
        if isinstance(session_id, str) and session_id.strip() and session_id not in registered:
            self_sessions.remember(layout.self_sessions, session_id)
            registered.add(session_id)

    worker.stream_agent(
        [*argv, "--format", "stream-json", "-Q", "-q", prompt],
        layout,
        "",
        timeout,
        env=dict(os.environ, MEMU_BRIDGING_RUN="1", HERMES_HOME=str(hermes_home())),
        on_output=capture,
        stdin=subprocess.DEVNULL,
    )
    if not registered:
        raise RuntimeError("Hermes worker did not report a session_id; cannot exclude its history")  # noqa: TRY003
