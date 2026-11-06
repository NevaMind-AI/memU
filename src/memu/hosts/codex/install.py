"""Install and verify Codex memory hooks in one invocation."""

# Localized diagnostics belong beside their installation gates.
# ruff: noqa: TRY003, RUF001

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from memu.hosts import installation
from memu.hosts.codex import cli_prepare, prompt_hook_install
from memu.hosts.install_language import text
from memu.hosts.installation import Blocked, Failed

STAGES = (
    "检查安装条件",
    "准备 memU 与记忆后端",
    "准备 Codex CLI",
    "配置自动记忆与检索",
    "完成安装检查",
)
NOTICE = "如果你使用 Codex Desktop，且以前自行安装过 memU 定时任务，现在可以自行暂停或移除它们，避免重复处理记忆。"


def _home() -> Path:
    return Path.home() / ".codex"


async def _command(argv: list[str]) -> int:
    from memu.hosts.codex.cli import build_parser

    args = build_parser().parse_args(argv)
    return int(await args.handler(args))


def _inspect() -> None:
    hooks = _home() / "hooks.json"
    if hooks.is_symlink():
        raise Blocked("hook 配置为符号链接，请先检查其归属和目标。")
    if hooks.exists():
        data = json.loads(hooks.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
            raise Blocked("~/.codex/hooks.json 格式无效；请先修复，安装器不会覆盖。")
    _check_cleanup()


def _check_cleanup() -> None:
    installation.check_cleanup(_home(), "memu-codex", "AGENTS.md")


async def _stage(stage: int, args: argparse.Namespace) -> None:
    if stage == 1:
        _inspect()
    elif stage == 2:
        await installation.backend(args, _command)
    elif stage == 3:
        _prepare_host(args)
    elif stage == 4:
        # Registration includes app-server read-back of both hooks and their trust state.
        prompt_hook_install.install(args.codex, _home() / "hooks.json", args.cwd, str(args.base_dir), default_home=True)
    else:
        _check_cleanup()
        if await _command(["remove-instruction"]):
            raise Blocked("旧检索指令清理失败。")


def _prepare_host(args: argparse.Namespace) -> None:
    result = cli_prepare.prepare(args.codex, install_missing=args.install_missing)
    if (
        result.get("reason") == "missing"
        and not args.non_interactive
        and not args.install_missing
        and input(text("是否使用官方安装器补装 Codex？[y/N] ")).strip().lower() == "y"
    ):
        result = cli_prepare.prepare(args.codex, install_missing=True)
    detail = {
        "missing": "未找到 Codex CLI。添加 --install-missing 可使用官方安装器补装。",
        "install_incomplete": "官方安装器已退出，但仍未找到 Codex CLI。请检查安装器输出或使用 --codex PATH 指定程序。",
        "startup_failed": "Codex CLI 启动检查失败，codex --version 未返回有效版本。请检查程序是否完整。",
        "not_found": "指定的 Codex 程序不存在，请检查 --codex 路径。",
    }.get(result.get("reason", ""), result.get("detail", ""))
    if result["status"] == "blocked":
        raise Blocked(detail)
    if result["status"] != "passed":
        reason = result.get("reason")
        if reason == "download_http_error":
            detail = text("官方安装器下载失败：HTTP {code}。服务器拒绝了下载请求。", code=str(result["http_status"]))
        elif reason == "download_connection_error":
            detail = text("无法连接官方安装器下载服务，请检查网络和代理设置。") + "\n" + result["detail"]
        elif reason == "timeout":
            detail = text("Codex 命令等待超过 {seconds} 秒，已停止。", seconds=str(result["timeout_seconds"]))
        elif reason == "installer_exit":
            detail = text("官方安装器退出，错误码 {code}。请查看上方安装器输出。", code=str(result["exit_code"]))
        else:
            detail = text(detail)
        raise Failed(detail + "\n" + text("可以在网络恢复后重新运行，或自行安装 Codex 后使用 --codex PATH 指定程序。"))
    args.codex = result["executable"]
    print(text("   独立 Codex CLI：{path}", path=args.codex), flush=True)


async def run(args: argparse.Namespace) -> int:
    args.cwd = args.cwd.expanduser().resolve()
    previous_home = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(_home())
    try:
        return await installation.run(
            args,
            host="codex",
            stages=STAGES,
            execute=_stage,
            welcome="\n👋 欢迎安装 memU\n   为 Codex 配置自动检索和后台记忆。",
            completion={"notice": NOTICE},
        )
    finally:
        if previous_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = previous_home


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Install and verify Codex memory hooks in one invocation")
    installation.add_arguments(parser, "codex")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex", default=None)
    parser.set_defaults(handler=run)
