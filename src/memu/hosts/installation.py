"""Shared CLI installation lifecycle for host adapters."""

# ruff: noqa: TRY003, RUF001
from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import io
import json
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TextIO

from memu import config_file, events
from memu.hosts import instruction
from memu.hosts.hooks.admission import workspace_lock
from memu.hosts.install_language import LANGUAGE, text


class Blocked(Exception):
    """A missing input or host-side action that permits a later retry."""

    def __str__(self) -> str:
        return text(super().__str__())


class Failed(Blocked):
    """A diagnosed installation failure safe to show to the caller."""


async def backend(args: argparse.Namespace, invoke: Callable[[list[str]], Awaitable[int]]) -> None:
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
        if await invoke(argv):
            raise Blocked("后端配置未通过保护检查；已有配置保留，请检查 config 诊断。")
    diagnostics = io.StringIO()
    with contextlib.redirect_stdout(sys.stdout if args.json else diagnostics):
        status = await invoke(["doctor", "--backend-only"])
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


def _select_language(args: argparse.Namespace) -> None:
    language = args.language
    if language not in {"en", "zh"}:
        language = "en"
        if not args.non_interactive and sys.stdin.isatty():
            with contextlib.redirect_stdout(sys.stderr):
                language = input("\n🚀 memU Installer\nLanguage: en/zh [en]: ").strip().lower() or "en"
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
        print(f"\n{icon}  {stage}/5  {result['title']}", file=output, flush=True)
    elif status == "passed":
        print(f"   ✅ {text('已完成')} · {elapsed:.1f}s", file=output, flush=True)
    else:
        label, symbol = {
            "blocked": (text("安装暂时无法继续"), "⚠️"),
            "cancelled": (text("安装已取消"), "👋"),
        }.get(status, (text("安装未完成"), "❌"))
        detail = "\n".join("   " + line for line in result.get("detail", "").splitlines())
        print(f"\n{symbol}  {label}\n{detail}", file=output, flush=True)
    if result.get("complete"):
        print(text("\n🎉 memU 安装完成！自动检索和后台记忆已就绪。"), file=output, flush=True)
    if result.get("notice"):
        print("\n💡 " + result["notice"], file=output, flush=True)


def _stop_reason(exc: BaseException, host: str) -> tuple[str, int, str]:
    if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError)):
        return "cancelled", 130, ""
    if isinstance(exc, EOFError):
        return (
            "blocked",
            2,
            text("输入已结束，安装已停止。请在交互终端重新运行，或使用 --non-interactive 并提供所需参数。"),
        )
    if isinstance(exc, Failed):
        events.record_cli_error(exc, command="install", host=host)
        return "failed", 1, str(exc)
    return "blocked", 2, str(exc)


async def run(
    args: argparse.Namespace,
    *,
    host: str,
    stages: tuple[str, ...],
    execute: Callable[[int, argparse.Namespace], Awaitable[None]],
    welcome: str,
    completion: dict[str, Any],
) -> int:
    started = time.monotonic()
    stage = 1
    language_token = LANGUAGE.set(args.language or "en")
    output = sys.stdout

    def emit(status: str, **extra: Any) -> None:
        elapsed = time.monotonic() - started
        result = {
            "stage": stage,
            "title": text(stages[stage - 1]),
            "status": status,
            "elapsed_ms": int(elapsed * 1000),
            **extra,
        }
        _render_progress(result, output, json_output=args.json)

    try:
        args.base_dir = args.base_dir.expanduser().resolve()
        args.base_dir.mkdir(parents=True, exist_ok=True)
        _select_language(args)
        started = time.monotonic()
        if not args.json:
            print(text(welcome), file=output, flush=True)
        # Installation edits configuration, while workers own processing files.
        lock_dir = args.base_dir / ".install"
        lock_dir.mkdir(exist_ok=True)
        with workspace_lock(lock_dir) as acquired:
            if not acquired:
                emit("blocked", detail=text("另一个安装进程正在运行，请稍后重新发起安装。"), complete=False)
                return 2
            events.record(events.CLI_INSTALL_STARTED, host=host)
            for stage in range(1, len(stages) + 1):
                emit("started")
                diagnostics = io.StringIO()
                try:
                    destination = sys.stderr if args.json else (diagnostics if stage in {4, 5} else output)
                    with contextlib.redirect_stdout(destination):
                        await execute(stage, args)
                except Exception:
                    print(diagnostics.getvalue(), end="", file=sys.stderr, flush=True)
                    raise
                if not args.json and stage == 2:
                    mode = config_file.read().get("MEMU_MEMORY_MODE", "local")
                    print(text("   {mode} 后端连接正常", mode=mode), file=output, flush=True)
                if stage == len(stages):
                    events.record(events.CLI_INSTALL_SUCCEEDED, host=host)
                    emit(
                        "passed",
                        complete=True,
                        **{key: text(value) if isinstance(value, str) else value for key, value in completion.items()},
                    )
                else:
                    emit("passed", complete=False)
            return 0
    except (KeyboardInterrupt, asyncio.CancelledError, EOFError, Blocked) as exc:
        status, code, detail = _stop_reason(exc, host)
        emit(status, detail=detail, complete=False)
        return code
    except (OSError, ValueError, TypeError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        # Keep credential-bearing provider errors out of machine-readable progress.
        events.record_cli_error(exc, command="install", host=host)
        emit("failed", detail=f"{type(exc).__name__}: {text('请检查本地诊断并重新运行安装。')}", complete=False)
        return 1
    finally:
        LANGUAGE.reset(language_token)


def add_arguments(parser: argparse.ArgumentParser, host: str) -> None:
    """Register the common installation inputs; hosts add their executable selection."""
    parser.add_argument("--language", choices=("en", "zh"))
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--base-dir", type=Path, default=Path("~/.memu/hosts") / host)
    parser.add_argument("--install-missing", action="store_true")
    parser.add_argument("--backend", choices=("cloud", "local"))
    for name in ("cloud-api-key", "db", "embed-provider", "embed-model", "embed-api-key", "embed-base-url"):
        parser.add_argument("--" + name, default="")


def check_cleanup(home: Path, binary: str, instruction_name: str) -> None:
    skill = home / "skills/memu-retrieve/SKILL.md"
    if skill.exists() or skill.is_symlink():
        if (
            not skill.is_file()
            or skill.parent.is_symlink()
            or skill.is_symlink()
            or set(skill.parent.iterdir()) != {skill}
        ):
            raise Blocked("旧检索 skill 含额外文件或链接，请由 Agent 确认归属后定向清理。")
        if skill.read_text(encoding="utf-8") != instruction.skill_document(binary):
            raise Blocked("旧检索 skill 与内置版本不同，请由 Agent 检查编辑和归属后定向清理。")
    agents = home / instruction_name
    if agents.exists() or agents.is_symlink():
        if agents.is_symlink():
            raise Blocked("全局指令为链接，请先检查归属和目标。")
        known = {instruction.block(binary, skill=True).strip(), instruction.block(binary).strip()}
        for match in instruction._block_re(binary).finditer(agents.read_text(encoding="utf-8")):
            if match.group().strip() not in known:
                raise Blocked("旧检索 managed block 含未知编辑，请由 Agent 检查后定向清理。")
