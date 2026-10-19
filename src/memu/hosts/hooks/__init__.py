"""Minimal Codex notify hook support for the first record-run PR."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from memu.hosts.bridging import Layout


@dataclass(frozen=True)
class HeadlessAgent:
    argv: tuple[str, ...]
    timeout_seconds: int = 60 * 60


@dataclass(frozen=True)
class HookSpec:
    agent: HeadlessAgent
    installer: CodexNotifyHook
    launch_console: Callable[[list[str], Layout, str, bool], None] | None = None
    stream_output: Callable[[list[str], Layout, str, int], None] | None = None


def jobs_prompt(layout: Layout) -> str:
    return (
        "Process the memU self-evolve jobs. List "
        f"{layout.jobs}/*.txt and process them in ascending numeric order. "
        "Read each job and follow its instructions exactly. Finish one job before "
        "starting the next. Do not run memu-codex prepare or commit; the worker "
        "runs those commands itself."
    )


def pending_jobs(layout: Layout) -> list[Path]:
    return sorted(layout.jobs.glob("*.txt"))


def run_agent(
    agent: HeadlessAgent,
    layout: Layout,
    *,
    executable: str = "",
    stream_output: Callable[[list[str], Layout, str, int], None] | None = None,
) -> None:
    argv = [token.replace("{base}", str(layout.base)) for token in agent.argv]
    resolved = executable or shutil.which(argv[0])
    if not resolved:
        raise RuntimeError(f"`{argv[0]}` is not on PATH")  # noqa: TRY003
    if stream_output is not None:
        stream_output([resolved, *argv[1:]], layout, jobs_prompt(layout), agent.timeout_seconds)
        return
    result = subprocess.run(  # noqa: S603
        [resolved, *argv[1:]],
        input=jobs_prompt(layout),
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=layout.base,
        capture_output=True,
        timeout=agent.timeout_seconds,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip()[-2000:])
    if result.stderr.strip():
        print(result.stderr.strip()[-4000:], file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f"`{argv[0]}` exited {result.returncode}")  # noqa: TRY003


def spawn_detached(argv: Sequence[str], layout: Layout) -> None:
    log = layout.base / "hook.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as output:
        output.write("\n=== hook run ===\n")
        output.flush()
        subprocess.Popen(  # noqa: S603
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            cwd=layout.base,
            start_new_session=sys.platform != "win32",
        )


class CodexNotifyHook:
    """Install a notify command when Codex has no notify command yet.

    Existing notify chaining is a separate acceptance item. Refusing to overwrite
    it keeps this first slice safe and makes that missing capability explicit.
    """

    def __init__(self, path: str | Path = "~/.codex/config.toml") -> None:
        self.path = Path(os.path.expanduser(str(path)))

    def _notify(self) -> list[str] | None:
        import tomllib

        if not self.path.exists():
            return None
        value = tomllib.loads(self.path.read_text(encoding="utf-8")).get("notify")
        if value is None:
            return None
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("Codex notify must be a string array")  # noqa: TRY003
        return value

    def install(self, argv: list[str]) -> None:
        current = self._notify()
        if current is not None and current != argv:
            raise ValueError(  # noqa: TRY003
                f"{self.path} already defines notify; remove it or use the notify-chain PR"
            )
        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        if current == argv:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"notify = {json.dumps(argv)}\n{text}", encoding="utf-8")

    def remove(self, binary: str) -> None:
        import re
        import tomllib

        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        current = self._notify()
        if not current or Path(current[0]).name.removesuffix(".exe") != binary:
            return
        updated = re.sub(r"(?m)^notify\s*=\s*\[[^\n]*\]\n?", "", text, count=1)
        tomllib.loads(updated)
        self.path.write_text(updated, encoding="utf-8")
