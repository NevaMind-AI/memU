"""Run Hermes through its CLI for the shared bridging worker."""

from __future__ import annotations

import os
import subprocess

from memu.hosts.bridging import Layout
from memu.hosts.hermes.sessions import hermes_home
from memu.hosts.hooks import worker


def stream_agent(argv: list[str], layout: Layout, prompt: str, timeout: int) -> None:
    worker.stream_agent(
        [*argv, "-z", prompt],
        layout,
        "",
        timeout,
        env=dict(os.environ, MEMU_BRIDGING_RUN="1", HERMES_HOME=str(hermes_home())),
        stdin=subprocess.DEVNULL,
    )
