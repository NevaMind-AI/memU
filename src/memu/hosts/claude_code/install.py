"""One-invocation Claude installation with CLI-owned backend and hook configuration."""

# Localized diagnostics belong beside their installation gates.
# ruff: noqa: TRY003, TRY301, TRY300, RUF001

from __future__ import annotations

import argparse
import asyncio
import contextlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from memu import events
from memu.hosts import instruction
from memu.hosts.claude_code import cli_prepare, hook_install
from memu.hosts.codex import install as lifecycle
from memu.hosts.codex.install_language import LANGUAGE
from memu.hosts.hooks.admission import workspace_lock

STAGES = (
    "Inspect installation",
    "Verify memory backend",
    "Prepare Claude CLI",
    "Configure memory hooks",
    "Finish installation",
)
ZH_STAGES = ("检查安装条件", "准备记忆后端", "准备 Claude CLI", "配置记忆 hooks", "完成安装检查")


async def _command(argv: list[str]) -> int:
    from memu.hosts.claude_code.cli import SPEC
    from memu.hosts.host_cli import build_parser

    args = build_parser(SPEC).parse_args(argv)
    return int(await args.handler(args))


def _check_cleanup() -> None:
    home = hook_install.home()
    binary = "memu-claude-code"
    skill = home / "skills/memu-retrieve/SKILL.md"
    if skill.exists() and (
        skill.is_symlink()
        or skill.parent.is_symlink()
        or set(skill.parent.iterdir()) != {skill}
        or skill.read_text(encoding="utf-8") != instruction.skill_document(binary)
    ):
        raise lifecycle.Blocked("Legacy retrieval skill has user edits or links; inspect ownership before cleanup")
    target = home / "CLAUDE.md"
    if target.exists():
        if target.is_symlink():
            raise lifecycle.Blocked("CLAUDE.md is a symlink; inspect ownership before cleanup")
        known = {instruction.block(binary, skill=True).strip(), instruction.block(binary).strip()}
        if any(
            match.group().strip() not in known
            for match in instruction._block_re(binary).finditer(target.read_text(encoding="utf-8"))
        ):
            raise lifecycle.Blocked("Legacy retrieval instruction has user edits; inspect before cleanup")


def _prepare_host(args: argparse.Namespace) -> None:
    try:
        executable = cli_prepare.prepare(args.claude, install_missing=args.install_missing)
    except FileNotFoundError:
        if args.non_interactive or args.install_missing or args.claude:
            raise
        if (
            input("Install the missing standalone Claude CLI using the official installer? [y/N] ").strip().lower()
            != "y"
        ):
            raise lifecycle.Blocked("Standalone Claude CLI required; rerun with --install-missing") from None
        executable = cli_prepare.prepare(install_missing=True)
    if not cli_prepare.auth_status(executable):
        raise lifecycle.Blocked(
            "Claude CLI is not authenticated. Run `claude auth login` or configure your provider credentials, then retry."
        )
    print(f"   Claude CLI: {executable}", flush=True)


async def _stage(stage: int, args: argparse.Namespace) -> None:
    if stage == 1:
        _, _, settings = hook_install.read()
        if settings.get("disableAllHooks") is True or settings.get("allowManagedHooksOnly") is True:
            raise lifecycle.Blocked("Claude settings disable user hooks; enable them before installation")
        _check_cleanup()
    elif stage == 2:
        await lifecycle._backend(args, _command)
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
    stage = 1
    started = time.monotonic()
    token = LANGUAGE.set(args.language or "en")
    output = sys.stdout

    def emit(status: str, **extra: Any) -> None:
        titles = ZH_STAGES if LANGUAGE.get() == "zh" else STAGES
        lifecycle._render_progress(
            {
                "stage": stage,
                "title": titles[stage - 1],
                "status": status,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                **extra,
            },
            output,
            json_output=args.json,
        )

    try:
        lifecycle._select_language(args)
        started = time.monotonic()
        if not args.json:
            print(
                "\n👋  欢迎安装 memU · Claude Code" if args.language == "zh" else "\n👋  Welcome to memU · Claude Code",
                file=output,
            )
        args.base_dir = args.base_dir.expanduser().resolve()
        lock = args.base_dir / ".install"
        lock.mkdir(parents=True, exist_ok=True)
        with workspace_lock(lock) as acquired:
            if not acquired:
                raise lifecycle.Blocked("Another Claude installation is running; end this attempt and retry later")
            events.record(events.CLI_INSTALL_STARTED, host="claude-code")
            for stage in range(1, 6):
                emit("started")
                with contextlib.redirect_stdout(sys.stderr if args.json else output):
                    await _stage(stage, args)
                if stage == 5:
                    events.record(events.CLI_INSTALL_SUCCEEDED, host="claude-code")
                    notice = (
                        "重新打开 Claude 会话使 hook 配置生效。如曾配置 memU 定时任务，请自行暂停或移除。"
                        if args.language == "zh"
                        else "Open a new Claude session to load hooks. Pause or remove any previously configured memU schedules yourself."
                    )
                    emit("passed", complete=True, notice=notice, hook_verification="local_settings_readback")
                else:
                    emit("passed", complete=False)
        return 0
    except (KeyboardInterrupt, asyncio.CancelledError):
        emit("cancelled", complete=False)
        return 130
    except (EOFError, lifecycle.Blocked, FileNotFoundError) as exc:
        emit(
            "blocked",
            detail=str(exc) or "Input ended; rerun in a terminal or supply non-interactive options.",
            complete=False,
        )
        return 2
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        events.record_cli_error(exc, command="install", host="claude-code")
        # Backend exceptions may contain provider credentials; local stage diagnostics do not.
        detail = (
            f"{type(exc).__name__}: {exc}"
            if stage in (1, 3, 4)
            else f"{type(exc).__name__}: installation failed; check local diagnostics and retry."
        )
        emit("failed", detail=detail, complete=False)
        return 1
    finally:
        LANGUAGE.reset(token)


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Configure Claude memory hooks in one invocation")
    parser.add_argument("--language", choices=("en", "zh"))
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--base-dir", type=Path, default=Path("~/.memu/hosts/claude-code"))
    parser.add_argument("--claude", default=None)
    parser.add_argument("--install-missing", action="store_true")
    parser.add_argument("--backend", choices=("cloud", "local"))
    for name in ("cloud-api-key", "db", "embed-provider", "embed-model", "embed-api-key", "embed-base-url"):
        parser.add_argument("--" + name, default="")
    parser.set_defaults(handler=run)
