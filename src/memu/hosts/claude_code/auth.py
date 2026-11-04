"""Interactive Claude CLI authentication choices; credentials stay out of diagnostics."""

# ruff: noqa: TRY003, RUF001
from __future__ import annotations

import argparse
import getpass
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from memu.hosts import installation
from memu.hosts.claude_code import cli_prepare, hook_install
from memu.hosts.hooks.admission import workspace_lock
from memu.hosts.install_language import LANGUAGE, text


def _provider() -> None:
    endpoint = input(text("   API 地址：")).strip()
    url = urlsplit(endpoint)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise installation.Blocked("Enter an HTTP(S) endpoint without credentials, query or fragment.")
    kind = input(text("   凭据类型 [api-key/token]（默认 api-key）：")).strip() or "api-key"
    if kind not in {"api-key", "token"}:
        raise installation.Blocked("Choose api-key or token.")
    secret = getpass.getpass(text("   凭据（明文保存到 ~/.claude/settings.json）：")).strip()
    if not secret:
        raise installation.Blocked("No credential supplied; configuration was not changed.")
    lock = hook_install.home() / ".memu-hooks-lock"
    lock.mkdir(parents=True, exist_ok=True)
    with workspace_lock(lock) as acquired:
        if not acquired:
            raise installation.Blocked("Another Claude settings update is running.")
        path, original, data = hook_install.read()
        configured = data.setdefault("env", {})
        if not isinstance(configured, dict):
            raise installation.Blocked("Claude settings env must be an object.")
        if configured.get("ANTHROPIC_API_KEY") or configured.get("ANTHROPIC_AUTH_TOKEN"):
            raise installation.Blocked(
                "Existing credentials were preserved; inspect your provider configuration before replacing them."
            )
        configured["ANTHROPIC_BASE_URL"] = endpoint
        configured["ANTHROPIC_API_KEY" if kind == "api-key" else "ANTHROPIC_AUTH_TOKEN"] = secret
        hook_install._write(path, original, data)


def configure(executable: Path, *, method: str | None, non_interactive: bool) -> None:
    if cli_prepare.auth_status(executable):
        print(text("   认证：已配置，待请求验证。"))
        return
    if non_interactive:
        raise installation.Blocked(
            "Claude authentication is missing. Run `memu-claude-code auth` to choose account login, "
            "manual API key / token entry, external configuration (including cc-switch), or configure later."
        )
    if method is None:
        print(
            text(
                "\n   🔐  配置认证\n   1. Claude 账号登录\n   2. 输入 API key / token\n   3. cc-switch 等外部工具\n   4. 稍后配置"
            )
        )
        method = {"1": "login", "2": "provider", "3": "external", "4": "later"}.get(
            input(text("   请选择 [1/2/3/4]：")).strip()
        )
    print()
    if method == "later":
        raise installation.Blocked("认证已暂缓；后台记忆尚不可用。稍后运行 `memu-claude-code auth`，再重新安装。")
    if method == "login":
        env = cli_prepare.standalone_env()
        result = subprocess.run([str(executable), "auth", "login"], env=env, check=False)  # noqa: S603
        if result.returncode:
            raise installation.Blocked("Claude 登录未完成；请重新运行 `memu-claude-code auth`。")
    elif method == "provider":
        _provider()
    elif method == "external":
        input(text("   请在 cc-switch 等工具中完成配置，按回车重新检查："))
    else:
        raise installation.Blocked("请选择 login、provider、external 或 later。")
    print()
    if not cli_prepare.auth_status(executable):
        raise installation.Blocked(
            "Claude still reports no authentication. Run `memu-claude-code auth` to retry; background memory is not ready."
        )
    print(text("   认证：已配置，待请求验证。"))


async def run(args: argparse.Namespace) -> int:
    token = LANGUAGE.set(args.language or "en")
    try:
        configure(cli_prepare.prepare(args.claude), method=args.method, non_interactive=args.non_interactive)
    except (EOFError, installation.Blocked, FileNotFoundError) as exc:
        print(str(exc) or "Input ended; authentication was not completed.")
        return 2
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Authentication check failed: {type(exc).__name__}; retry or inspect Claude configuration.")
        return 1

    else:
        return 0
    finally:
        LANGUAGE.reset(token)


def register(sub: Any) -> None:
    parser = sub.add_parser("auth", help="Configure Claude CLI account login or provider authentication")
    parser.add_argument("--language", choices=("en", "zh"))
    parser.add_argument("--method", choices=("login", "provider", "external", "later"))
    parser.add_argument("--claude", default=None)
    parser.add_argument("--non-interactive", action="store_true")
    parser.set_defaults(handler=run)
