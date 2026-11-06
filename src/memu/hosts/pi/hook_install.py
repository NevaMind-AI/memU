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
    home = agent_dir()
    destination = target()
    content = extension_content(base)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False, suffix=".tmp") as temporary:
        temporary.write(content.encode("utf-8"))
    try:
        Path(temporary.name).replace(destination)
    finally:
        Path(temporary.name).unlink(missing_ok=True)
    for name in ("AGENTS.md", "AGENTS.override.md"):
        instruction.remove(home / name, "memu-pi")
    skill = instruction.skill_path(home / "skills")
    if skill.is_file() and "memu-pi retrieve" in skill.read_text(encoding="utf-8"):
        instruction.remove_skill(home / "skills")
    return destination


async def _install(args: argparse.Namespace) -> int:
    print(f"Installed: {install(Path(args.base_dir))}")
    print("Run /reload or open a new pi session to load the memU extension.")
    return 0


async def _remove(args: argparse.Namespace) -> int:
    del args
    target = agent_dir() / "extensions/memu-retrieval.ts"
    if target.is_symlink():
        raise ValueError("Refusing to remove a symlinked pi extension")  # noqa: TRY003
    if target.exists():
        if not target.read_text(encoding="utf-8").startswith(MARKER):
            raise ValueError("Refusing to remove an unowned pi extension")  # noqa: TRY003
        target.unlink()
    print("Removed memU extension. Run /reload or open a new pi session.")
    return 0


def register(sub: Any) -> None:
    memorize_hook.register(sub)
    for name, handler, help_text in (
        ("install-prompt-hook", _install, "Install pi's asynchronous retrieval and memorization extension"),
        ("prompt-hook", prompt_hook, "Retrieve context for a pi input event on stdin"),
        ("remove-prompt-hook", _remove, "Remove only memU's pi extension"),
    ):
        parser = sub.add_parser(name, help=help_text)
        parser.add_argument("--base-dir", default="~/.memu/hosts/pi")
        parser.set_defaults(handler=handler)
