"""Configure memU for the user's existing pi environment."""

# ruff: noqa: TRY003, RUF001
from __future__ import annotations

import argparse
import shutil
from typing import Any

from memu.hosts import installation as lifecycle
from memu.hosts.hooks.admission import workspace_lock
from memu.hosts.install_language import text
from memu.hosts.pi import hook_install

STAGES = ("检查安装条件", "准备 memU 与记忆后端", "配置并检查 pi 扩展")


async def _command(argv: list[str]) -> int:
    from memu.hosts.host_cli import build_parser
    from memu.hosts.pi.cli import SPEC

    args = build_parser(SPEC).parse_args(argv)
    return int(await args.handler(args))


def _check_files() -> None:
    try:
        hook_install.target()
    except ValueError:
        raise lifecycle.Blocked("pi 扩展安装位置已有非 memU 文件或链接，请检查归属后重试。") from None


async def _stage(stage: int, args: argparse.Namespace) -> None:
    if stage == 1:
        executable = shutil.which("pi")
        if not executable:
            raise lifecycle.Blocked("未在 PATH 中找到 pi；请在可运行 pi 的终端中重新安装 memU。")
        _check_files()
        print(text("   pi：{path}", path=executable))
    elif stage == 2:
        await lifecycle.backend(args, _command)
    else:
        lock = hook_install.agent_dir() / ".memu-hooks-lock"
        lock.mkdir(parents=True, exist_ok=True)
        with workspace_lock(lock) as acquired:
            if not acquired:
                raise lifecycle.Blocked("另一个 pi 扩展安装正在运行，请稍后重试。")
            _check_files()
            path = hook_install.install(args.base_dir)
            if path.read_text(encoding="utf-8") != hook_install.extension_content(args.base_dir):
                raise lifecycle.Failed("pi 扩展回读验证失败，请重新运行安装。")


async def run(args: argparse.Namespace) -> int:
    return await lifecycle.run(
        args,
        host="pi",
        stages=STAGES,
        execute=_stage,
        welcome="\n👋  欢迎安装 memU · pi",
        completion={
            "notice": "在 pi 中运行 /reload 或重新打开会话，启用自动检索和后台记忆。",
            "hook_verification": "local_extension_readback",
        },
    )


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Configure pi memory hooks in one invocation")
    lifecycle.add_arguments(parser, "pi", install_missing=False)
    parser.set_defaults(handler=run)
