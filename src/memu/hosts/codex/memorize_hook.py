"""Start background memorization from a Codex UserPromptSubmit event."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from memu.hosts.bridging import Layout
from memu.hosts.codex import notify_console

BACKGROUND_ENV = "MEMU_CODEX_MEMORIZE"


async def _cmd_memorize_hook(args: argparse.Namespace) -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get("hook_event_name") != "UserPromptSubmit":
            raise ValueError("expected a UserPromptSubmit object")  # noqa: TRY003, TRY301
        if os.environ.get(BACKGROUND_ENV) != "1":
            layout = Layout.default("codex", args.base_dir) if args.base_dir is not None else Layout.default("codex")
            notify_console.launch_background(
                ["hook-run", "--base-dir", str(layout.base), "--agent", args.agent, "--session-dir", args.session_dir],
                layout,
                "codex",
            )
    except (OSError, ValueError, TypeError) as exc:
        print(f"memU memorize hook failed: {exc}", file=sys.stderr)
    print("{}")
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("memorize-hook", help="Start background memory processing on prompt submission")
    parser.add_argument("--base-dir", default=None)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--session-dir", default="~/.codex/sessions")
    parser.set_defaults(handler=_cmd_memorize_hook)
