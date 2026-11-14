"""Remove owned Claude hooks and retrieval artifacts without requiring Claude CLI."""

# ruff: noqa: TRY300

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from memu.hosts import instruction
from memu.hosts.claude_code import hook_install
from memu.hosts.hooks.admission import workspace_lock
from memu.hosts.install_language import LANGUAGE


async def run(args: argparse.Namespace) -> int:
    lock = hook_install.home() / ".memu-hooks-lock"
    lock.mkdir(parents=True, exist_ok=True)
    try:
        with workspace_lock(lock) as acquired:
            if not acquired:
                print("Another Claude settings update is running", file=sys.stderr)
                return 2
            home = hook_install.home()
            instruction.check_skill_cleanup(home / "skills", "memu-claude-code")
            count = hook_install.uninstall()
            cleaned = instruction.cleanup([home / "CLAUDE.md"], "memu-claude-code", skills_dir=home / "skills")
        notice = "Inspect historical schedules with memu-claude-code docs uninstall; open a fresh Claude session."
        if args.json:
            print(
                json.dumps({
                    "status": "passed",
                    "removed": count,
                    "retrieval_artifacts_removed": len(cleaned),
                    "notice": notice,
                })
            )
        else:
            print(
                f"🧹  已移除 {count} 个 memU hook。" if args.language == "zh" else f"🧹  Removed {count} memU hook(s)."
            )
            print(notice)
        return 0
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"memU uninstall failed: {exc}", file=sys.stderr)
        return 1


def register(sub: Any) -> None:
    parser = sub.add_parser(
        "uninstall", help="Remove memU hooks and owned retrieval instructions/skills; preserve memory"
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--language", choices=("en", "zh"), default=LANGUAGE.get())
    parser.set_defaults(handler=run)
