"""Install memU's pi retrieval and memorization extension; preserve other extensions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Any

from memu.hosts import instruction
from memu.hosts.hooks.admission import workspace_lock
from memu.hosts.pi import memorize_hook
from memu.hosts.pi.prompt_hook import prompt_hook

MARKER = "// memU managed retrieval extension."


def agent_dir() -> Path:
    return Path(os.environ.get("PI_CODING_AGENT_DIR") or "~/.pi/agent").expanduser()


def target() -> Path:
    path = agent_dir() / "extensions/memu-retrieval.ts"
    if path.is_symlink() or (path.exists() and not path.read_text(encoding="utf-8").startswith(MARKER)):
        raise ValueError("Refusing to overwrite an unowned pi extension")  # noqa: TRY003
    return path


def extension_content(base: Path) -> str:
    template = files("memu.hosts.pi").joinpath("retrieval-extension.ts").read_text(encoding="utf-8")
    return template.replace("__MEMU_PYTHON__", json.dumps(sys.executable)).replace(
        "__MEMU_BASE_DIR__", json.dumps(str(base.expanduser().resolve()))
    )


def install(base: Path) -> Path:
    destination = target()
    content = extension_content(base)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False, suffix=".tmp") as temporary:
        temporary.write(content.encode("utf-8"))
    try:
        Path(temporary.name).replace(destination)
    finally:
        Path(temporary.name).unlink(missing_ok=True)
    return destination


async def _install(args: argparse.Namespace) -> int:
    print(f"Installed: {install(Path(args.base_dir))}")
    print("Run /reload or open a new pi session to load the memU extension.")
    return 0


async def _remove(args: argparse.Namespace) -> int:
    lock = agent_dir() / ".memu-hooks-lock"
    lock.mkdir(parents=True, exist_ok=True)
    with workspace_lock(lock) as acquired:
        if not acquired:
            print("Another pi extension update is running", file=sys.stderr)
            return 2
        destination = target()
        home = agent_dir()
        full = getattr(args, "cleanup_retrieval", False)
        if full:
            instruction.check_skill_cleanup(home / "skills", "memu-pi")
        removed = int(destination.exists())
        destination.unlink(missing_ok=True)
        cleaned = (
            instruction.cleanup(
                [home / "AGENTS.md", home / "AGENTS.override.md"], "memu-pi", skills_dir=home / "skills"
            )
            if full
            else []
        )
    notice = "Run /reload or open a new pi session to unload the memU extension."
    if full:
        notice += " Inspect historical schedules with memu-pi docs uninstall."
    if getattr(args, "json", False):
        print(
            json.dumps({
                "status": "passed",
                "removed": removed,
                "retrieval_artifacts_removed": len(cleaned),
                "notice": notice,
            })
        )
    else:
        print(f"🧹  Removed {removed} memU extension(s) and {len(cleaned)} retrieval artifact(s). {notice}")
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser(
        "uninstall", help="Remove memU's pi extension and owned retrieval instructions/skills; preserve memory"
    )
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=_remove, cleanup_retrieval=True)
    memorize_hook.register(sub)
    for name, handler, help_text in (
        ("install-prompt-hook", _install, "Install pi's asynchronous retrieval and memorization extension"),
        ("prompt-hook", prompt_hook, "Retrieve context for a pi input event on stdin"),
        ("remove-prompt-hook", _remove, "Remove only memU's pi extension"),
    ):
        parser = sub.add_parser(name, help=help_text)
        parser.add_argument("--base-dir", default="~/.memu/hosts/pi")
        parser.set_defaults(handler=handler)
