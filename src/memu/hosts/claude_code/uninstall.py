"""Remove only owned Claude memory hooks, including when Claude CLI is absent."""

# ruff: noqa: TRY300

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

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
            count = hook_install.uninstall()
        if args.json:
            print(json.dumps({"status": "passed", "removed": count}))
        else:
            print(
                f"🧹  已移除 {count} 个 memU hook。" if args.language == "zh" else f"🧹  Removed {count} memU hook(s)."
            )
        return 0
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"memU uninstall failed: {exc}", file=sys.stderr)
        return 1


def register(sub: Any) -> None:
    parser = sub.add_parser("uninstall", help="Remove only memU's Claude hooks; preserve configuration and memory")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--language", choices=("en", "zh"), default=LANGUAGE.get())
    parser.set_defaults(handler=run)
