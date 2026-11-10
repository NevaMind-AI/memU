"""Configure Hermes memory hooks using the shared installation lifecycle."""

from __future__ import annotations

import argparse
import shutil
from typing import Any

from memu.hosts import installation as lifecycle
from memu.hosts.hermes import hook_install
from memu.hosts.hooks.admission import workspace_lock

STAGES = ("检查安装条件", "准备 memU 与记忆后端", "Configuring and checking the Hermes plugin")


async def _command(argv: list[str]) -> int:
    from memu.hosts.hermes.cli import SPEC
    from memu.hosts.host_cli import build_parser

    args = build_parser(SPEC).parse_args(argv)
    return int(await args.handler(args))


async def _stage(stage: int, args: argparse.Namespace) -> None:
    if stage == 1:
        executable = shutil.which("hermes")
        if not executable:
            raise lifecycle.Blocked("Hermes was not found on PATH; open a terminal where hermes is available.")  # noqa: TRY003
        try:
            version = hook_install.check_version()
            hook_install.target()
        except (ValueError, RuntimeError) as exc:
            raise lifecycle.Blocked(str(exc)) from exc
        print(f"   Hermes {version}: {executable}")
    elif stage == 2:
        await lifecycle.backend(args, _command)
    else:
        lock = hook_install.home() / ".memu-hooks-lock"
        lock.mkdir(parents=True, exist_ok=True)
        with workspace_lock(lock) as acquired:
            if not acquired:
                raise lifecycle.Blocked("Another Hermes plugin update is running; retry later.")  # noqa: TRY003
            path = hook_install.install(args.base_dir)
            if (path / "__init__.py").read_text(encoding="utf-8") != hook_install.plugin_content(args.base_dir) or (
                path / "plugin.yaml"
            ).read_text(encoding="utf-8") != hook_install.MANIFEST:
                raise lifecycle.Failed("Hermes plugin readback verification failed; rerun installation.")  # noqa: TRY003


async def run(args: argparse.Namespace) -> int:
    return await lifecycle.run(
        args,
        host="hermes",
        stages=STAGES,
        execute=_stage,
        welcome="\nWelcome to memU · Hermes",
        completion={
            "notice": "Restart Hermes to load memory hooks. Remove any previously configured memU schedules separately.",
            "hook_verification": "local_plugin_and_injection_grant_readback",
        },
    )


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Configure Hermes memory hooks in one invocation")
    lifecycle.add_arguments(parser, "hermes", install_missing=False)
    parser.set_defaults(handler=run)
