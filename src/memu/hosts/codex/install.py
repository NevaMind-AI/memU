"""Install and verify Codex memory hooks in one invocation."""

# Localized diagnostics belong beside their installation gates.
# ruff: noqa: TRY003, RUF001

from __future__ import annotations

import argparse
import contextlib
import getpass
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, TextIO

from memu import config_file, events
from memu.hosts import instruction
from memu.hosts.codex import cli_prepare, prompt_hook_install
from memu.hosts.codex.install_language import LANGUAGE, text
from memu.hosts.codex.notify_console import _workspace_lock as workspace_lock

STAGES = (
    "检查安装条件",
    "准备 memU 与记忆后端",
    "准备 Codex CLI",
    "配置自动记忆与检索",
    "完成安装检查",
)
NOTICE = "如果你使用 Codex Desktop，且以前自行安装过 memU 定时任务，现在可以自行暂停或移除它们，避免重复处理记忆。"


class Blocked(Exception):
    """A missing input or host-side action that permits a later retry."""

    def __str__(self) -> str:
        return text(super().__str__())


class Failed(Blocked):
    """A diagnosed installation failure safe to show to the caller."""


def _home() -> Path:
    return Path.home() / ".codex"


async def _command(argv: list[str]) -> int:
    from memu.hosts.codex.cli import build_parser

    args = build_parser().parse_args(argv)
    return int(await args.handler(args))


async def _backend(args: argparse.Namespace) -> None:
    supplied = any(
        getattr(args, name)
        for name in ("cloud_api_key", "db", "embed_provider", "embed_model", "embed_api_key", "embed_base_url")
    )
    mode = args.backend
    existing = config_file.read()
    configured = (
        existing.get("MEMU_CLOUD_API_KEY") if existing.get("MEMU_MEMORY_MODE") == "cloud" else existing.get("MEMU_DB")
    )
    if not configured and mode is None:
        if args.non_interactive:
            raise Blocked("后端尚未配置；使用 --backend cloud 或 --backend local 提供配置。")
        mode = input(text("记忆后端 [cloud/local]：")).strip()
        if mode not in {"cloud", "local"}:
            raise Blocked("请选择 cloud 或 local。")
    if mode is not None or supplied:
        if mode is None:
            raise Blocked("提供后端配置时需明确 --backend cloud 或 local。")
        _backend_inputs(args, mode)
        argv = ["config", "--" + mode]
        for name in ("cloud_api_key", "db", "embed_provider", "embed_model", "embed_api_key", "embed_base_url"):
            if value := getattr(args, name):
                argv.extend(["--" + name.replace("_", "-"), value])
        if await _command(argv):
            raise Blocked("后端配置未通过保护检查；已有配置保留，请检查 config 诊断。")
    diagnostics = io.StringIO()
    with contextlib.redirect_stdout(sys.stdout if args.json else diagnostics):
        status = await _command(["doctor"])
    if status:
        print(diagnostics.getvalue(), end="", file=sys.stderr)
        raise Blocked("后端 doctor 未通过，请修复连接或配置后重跑。")


def _backend_inputs(args: argparse.Namespace, mode: str) -> None:
    if mode == "cloud" and not args.cloud_api_key and not config_file.read().get("MEMU_CLOUD_API_KEY"):
        if args.non_interactive:
            raise Blocked("Cloud 后端需要 --cloud-api-key 或已有配置。")
        args.cloud_api_key = getpass.getpass(text("memU Cloud API key："))
    if mode == "local" and not args.non_interactive and not config_file.read().get("MEMU_DB") and not args.db:
        args.db = input(text("本地数据库路径 [~/.memu/memu.sqlite3]：")).strip() or str(
            Path.home() / ".memu/memu.sqlite3"
        )
        args.db = str(Path(args.db).expanduser().resolve())
        args.embed_provider = args.embed_provider or input(text("Embedding provider [openai]：")).strip() or "openai"
        args.embed_model = args.embed_model or input(text("Embedding model [provider 默认]：")).strip()
        args.embed_base_url = args.embed_base_url or input(text("Embedding endpoint [provider 默认]：")).strip()
        args.embed_api_key = args.embed_api_key or getpass.getpass(text("Embedding API key（本地服务可使用占位值）："))
    if mode == "local" and args.db and "://" not in args.db:
        args.db = str(Path(args.db).expanduser().resolve())
    if mode == "local" and not args.db and not config_file.read().get("MEMU_DB"):
        raise Blocked("本地后端需要 --db 指定持久化存储。")


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
    skill = _home() / "skills/memu-retrieve/SKILL.md"
    if skill.is_file():
        if skill.parent.is_symlink() or skill.is_symlink() or set(skill.parent.iterdir()) != {skill}:
            raise Blocked("旧检索 skill 含额外文件或链接，请由 Agent 确认归属后定向清理。")
        if skill.read_text(encoding="utf-8") != instruction.skill_document("memu-codex"):
            raise Blocked("旧检索 skill 与内置版本不同，请由 Agent 检查编辑和归属后定向清理。")
    agents = _home() / "AGENTS.md"
    if agents.is_file():
        if agents.is_symlink():
            raise Blocked("全局指令为链接，请先检查归属和目标。")
        known = {instruction.block("memu-codex", skill=True).strip(), instruction.block("memu-codex").strip()}
        for match in instruction._block_re("memu-codex").finditer(agents.read_text(encoding="utf-8")):
            if match.group().strip() not in known:
                raise Blocked("旧检索 managed block 含未知编辑，请由 Agent 检查后定向清理。")


async def _stage(stage: int, args: argparse.Namespace) -> None:
    if stage == 1:
        _inspect()
    elif stage == 2:
        await _backend(args)
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


def _select_language(args: argparse.Namespace) -> None:
    language = args.language
    if language not in {"en", "zh"}:
        language = "en"
        if not args.non_interactive and sys.stdin.isatty():
            with contextlib.redirect_stdout(sys.stderr):
                language = input("\nmemU Installer\n语言 / Language: en/zh [en]: ").strip().lower() or "en"
            if language not in {"en", "zh"}:
                raise Blocked("Choose en or zh / 请选择 en 或 zh。")
    args.language = language
    LANGUAGE.set(language)


def _render_progress(result: dict[str, Any], output: TextIO, *, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(result, ensure_ascii=False), file=output, flush=True)
        return
    stage, status = result["stage"], result["status"]
    elapsed = result["elapsed_ms"] / 1000
    icon = ("🔎", "🧠", "🛠️", "🔗", "✨")[stage - 1]
    if status == "started":
        print(f"\n{icon} {stage}/5  {result['title']}", file=output, flush=True)
    elif status == "passed":
        print(f"   ✅ {text('已完成')} · {elapsed:.1f}s", file=output, flush=True)
    else:
        label = text("安装暂时无法继续") if status == "blocked" else text("安装未完成")
        symbol = "⚠️" if status == "blocked" else "❌"
        print(f"\n{symbol} {label}\n   {result.get('detail', '')}", file=output, flush=True)
    if result.get("complete"):
        print(text("\n🎉 memU 安装完成！自动检索和后台记忆已就绪。"), file=output, flush=True)
    if result.get("notice"):
        print("\n💡 " + result["notice"], file=output, flush=True)


async def _run_stage(stage: int, args: argparse.Namespace, output: TextIO) -> None:
    diagnostics = io.StringIO()
    try:
        destination = sys.stderr if args.json else (diagnostics if stage in {4, 5} else output)
        with contextlib.redirect_stdout(destination):
            await _stage(stage, args)
    except Exception:
        print(diagnostics.getvalue(), end="", file=sys.stderr, flush=True)
        raise
    if not args.json and stage == 2:
        mode = config_file.read().get("MEMU_MEMORY_MODE", "local")
        print(text("   {mode} 后端连接正常", mode=mode), file=output, flush=True)


async def run(args: argparse.Namespace) -> int:
    started = time.monotonic()
    args.base_dir = args.base_dir.expanduser().resolve()
    args.cwd = args.cwd.expanduser().resolve()
    args.base_dir.mkdir(parents=True, exist_ok=True)
    stage = 1
    language_token = LANGUAGE.set(args.language or "en")
    previous_home = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(_home())
    output = sys.stdout

    def emit(status: str, **extra: Any) -> None:
        elapsed = time.monotonic() - started
        result = {
            "stage": stage,
            "title": text(STAGES[stage - 1]),
            "status": status,
            "elapsed_ms": int(elapsed * 1000),
            **extra,
        }
        _render_progress(result, output, json_output=args.json)

    try:
        _select_language(args)
        started = time.monotonic()
        if not args.json:
            print(text("\n🚀 欢迎安装 memU\n   为 Codex 配置自动检索和后台记忆。"), file=output, flush=True)
        # Installation edits configuration, while workers own processing files.
        lock_dir = args.base_dir / ".install"
        lock_dir.mkdir(exist_ok=True)
        with workspace_lock(lock_dir) as acquired:
            if not acquired:
                emit("blocked", detail=text("另一个安装进程正在运行，请稍后重新发起安装。"), complete=False)
                return 2
            events.record(events.CLI_INSTALL_STARTED, host="codex")
            for stage in range(1, len(STAGES) + 1):
                emit("started")
                await _run_stage(stage, args, output)
                if stage == len(STAGES):
                    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
                    emit("passed", complete=True, notice=text(NOTICE))
                else:
                    emit("passed", complete=False)
            return 0
    except Failed as exc:
        events.record_cli_error(exc, command="install", host="codex")
        emit("failed", detail=str(exc), complete=False)
        return 1
    except Blocked as exc:
        emit("blocked", detail=str(exc), complete=False)
        return 2
    except (OSError, ValueError, TypeError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        # Keep credential-bearing provider errors out of machine-readable progress.
        events.record_cli_error(exc, command="install", host="codex")
        emit("failed", detail=f"{type(exc).__name__}: {text('请检查本地诊断并重新运行安装。')}", complete=False)
        return 1
    finally:
        LANGUAGE.reset(language_token)
        if previous_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = previous_home


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Install and verify Codex memory hooks in one invocation")
    parser.add_argument("--language", choices=("en", "zh"), help="Installer language (English or 中文)")
    parser.add_argument("--non-interactive", action="store_true", help="Return blockers instead of prompting")
    parser.add_argument("--json", action="store_true", help="Emit JSONL installation progress")
    parser.add_argument("--base-dir", type=Path, default=Path("~/.memu/hosts/codex"))
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex", default=None)
    parser.add_argument("--install-missing", action="store_true")
    parser.add_argument("--backend", choices=("cloud", "local"))
    for name in ("cloud-api-key", "db", "embed-provider", "embed-model", "embed-api-key", "embed-base-url"):
        parser.add_argument("--" + name, default="")
    parser.set_defaults(handler=run)
