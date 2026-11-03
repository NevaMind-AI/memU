"""One-invocation Claude installation with CLI-owned backend and hook configuration."""

# Localized diagnostics belong beside their installation gates.
# ruff: noqa: TRY003, RUF001

from __future__ import annotations

import argparse
from typing import Any

from memu.hosts import installation as lifecycle
from memu.hosts.claude_code import auth, cli_prepare, hook_install
from memu.hosts.hooks.admission import workspace_lock

STAGES = (
    "检查安装条件",
    "准备 memU 与记忆后端",
    "准备 Claude CLI",
    "配置自动记忆与检索",
    "完成安装检查",
)


async def _command(argv: list[str]) -> int:
    from memu.hosts.claude_code.cli import SPEC
    from memu.hosts.host_cli import build_parser

    args = build_parser(SPEC).parse_args(argv)
    return int(await args.handler(args))


def _check_cleanup() -> None:
    lifecycle.check_cleanup(hook_install.home(), "memu-claude-code", "CLAUDE.md")


def _prepare_host(args: argparse.Namespace) -> None:
    try:
        executable = cli_prepare.prepare(args.claude, install_missing=args.install_missing)
    except FileNotFoundError:
        if args.non_interactive or args.install_missing or args.claude:
            raise lifecycle.Blocked("Standalone Claude CLI unavailable; install it or use --install-missing") from None
        if (
            input("Install the missing standalone Claude CLI using the official installer? [y/N] ").strip().lower()
            != "y"
        ):
            raise lifecycle.Blocked("Standalone Claude CLI required; rerun with --install-missing") from None
        executable = cli_prepare.prepare(install_missing=True)
    auth.configure(executable, method=args.auth, non_interactive=args.non_interactive)
    print(f"   Claude CLI: {executable}", flush=True)


async def _stage(stage: int, args: argparse.Namespace) -> None:
    if stage == 1:
        _, _, settings = hook_install.read()
        if settings.get("disableAllHooks") is True or settings.get("allowManagedHooksOnly") is True:
            raise lifecycle.Blocked("Claude settings disable user hooks; enable them before installation")
        _check_cleanup()
    elif stage == 2:
        await lifecycle.backend(args, _command)
    elif stage == 3:
        _prepare_host(args)
    elif stage == 4:
        settings_lock = hook_install.home() / ".memu-hooks-lock"
        settings_lock.mkdir(parents=True, exist_ok=True)
        with workspace_lock(settings_lock) as acquired:
            if not acquired:
                raise lifecycle.Blocked("Another Claude settings update is running")
            hook_install.install(args.base_dir)
    else:
        _check_cleanup()
        home = hook_install.home()
        if await _command([
            "remove-instruction",
            "--path",
            str(home / "CLAUDE.md"),
            "--skills-dir",
            str(home / "skills"),
        ]):
            raise lifecycle.Blocked("Legacy retrieval instruction cleanup failed")


async def run(args: argparse.Namespace) -> int:
    return await lifecycle.run(
        args,
        host="claude-code",
        stages=STAGES,
        execute=_stage,
        welcome="\n👋  欢迎安装 memU · Claude Code",
        completion={
            "notice": "重新打开 Claude 会话使 hook 配置生效。如曾配置 memU 定时任务，请自行暂停或移除。",
            "hook_verification": "local_settings_readback",
        },
    )


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Configure Claude memory hooks in one invocation")
    lifecycle.add_arguments(parser, "claude-code")
    parser.add_argument("--claude", default=None)
    parser.add_argument(
        "--auth", choices=("login", "provider", "later"), help="Authentication choice when not configured"
    )
    parser.set_defaults(handler=run)
