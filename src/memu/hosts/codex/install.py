"""Staged Codex installation with explicit Desktop migration handoff."""

# Localized diagnostics belong beside their installation gates.
# ruff: noqa: TRY003, RUF001

from __future__ import annotations

import argparse
import contextlib
import getpass
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from memu import config_file, events
from memu.hosts import instruction
from memu.hosts.codex import cli_prepare, prompt_hook_install
from memu.hosts.codex.notify_console import _workspace_lock as workspace_lock

STAGES = (
    "检查安装条件",
    "准备 memU 与记忆后端",
    "准备 Codex CLI",
    "配置自动记忆与检索",
    "完成交接与安装检查",
)


class Blocked(Exception):
    """A missing input or host-side action that permits a later retry."""


def _home() -> Path:
    return Path.home() / ".codex"


async def _command(argv: list[str]) -> int:
    from memu.hosts.codex.cli import build_parser

    args = build_parser().parse_args(argv)
    return int(await args.handler(args))


def _snapshot(base: Path) -> dict[str, str]:
    # Installation never removes pipeline files. Detect unexpected mutations at finalization.
    return {
        str(path.relative_to(base)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(base.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and path.name != "install-state.json"
        and path.name != ".diagnostic.lock"
    }


def _evidence(path: Path | None, *, deleted: bool = False) -> dict[str, Any]:
    if path is None:
        raise Blocked("需要 Desktop Agent 提供 --migration-evidence；或确认是新装后使用 --new-install。")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("source") != "desktop":
        raise Blocked("迁移证据必须是 version=1、source=desktop 的 JSON 对象。")
    if data.get("inventory_complete") is not True or not isinstance(data.get("tasks"), list):
        raise Blocked("Desktop 任务清单尚未确认完整。")
    inventory = data.get("inventory_evidence_file")
    if (
        not isinstance(inventory, str)
        or not (path.parent / inventory).is_file()
        or not (path.parent / inventory).read_bytes().strip()
    ):
        raise Blocked("Desktop 任务清单缺少本地回读证据。")
    for task in data["tasks"]:
        _task_evidence(task, path, deleted=deleted)
    return data


def _task_evidence(task: Any, path: Path, *, deleted: bool) -> None:
    if not isinstance(task, dict) or not isinstance(task.get("id"), str) or not task["id"]:
        raise Blocked("迁移任务缺少 ID。")
    if task.get("owned") is not True:
        raise Blocked("任务归属尚未确认；请由 Desktop Agent 核实清单。")
    for field in ("deleted",) if deleted else ("paused", "idle"):
        if task.get(field) is not True:
            raise Blocked(f"Desktop 任务尚未确认 {field}：{task['id']}")
    required = ("definition_file", "delete_evidence_file") if deleted else ("definition_file", "pause_evidence_file")
    for field in required:
        value = task.get(field)
        target = path.parent / value if isinstance(value, str) else None
        if target is None or not target.is_file() or not target.read_bytes().strip():
            raise Blocked(f"Desktop 任务缺少本地证据文件：{field}")


def _migration(args: argparse.Namespace, state: dict[str, Any], *, deleted: bool = False) -> dict[str, Any]:
    if not args.agent and args.migration_evidence is None:
        return {"tasks": [], "source": "desktop_deferred"}
    local_tasks = list((_home() / "automations").glob("*/automation.toml"))
    if args.new_install and args.migration_evidence is None and not local_tasks and not state.get("task_ids"):
        return {"tasks": [], "source": "user_confirmed_new_install"}
    evidence = _evidence(args.migration_evidence, deleted=deleted)
    ids = sorted(task["id"] for task in evidence["tasks"])
    if len(ids) != len(set(ids)):
        raise Blocked("迁移清单包含重复任务 ID。")
    if "task_ids" in state and state["task_ids"] != ids:
        raise Blocked("迁移任务清单已改变，请恢复原清单或使用独立工作目录重新检查。")
    definitions = {
        task["id"]: hashlib.sha256((args.migration_evidence.parent / task["definition_file"]).read_bytes()).hexdigest()
        for task in evidence["tasks"]
    }
    if "task_definitions" in state and state["task_definitions"] != definitions:
        raise Blocked("迁移任务定义备份已改变，请保留原始定义。")
    state["task_definitions"] = definitions
    return evidence


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
        mode = input("记忆后端 [cloud/local]：").strip()
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
    if await _command(["doctor"]):
        raise Blocked("后端 doctor 未通过，请修复连接或配置后重跑。")


def _backend_inputs(args: argparse.Namespace, mode: str) -> None:
    if mode == "cloud" and not args.cloud_api_key and not config_file.read().get("MEMU_CLOUD_API_KEY"):
        if args.non_interactive:
            raise Blocked("Cloud 后端需要 --cloud-api-key 或已有配置。")
        args.cloud_api_key = getpass.getpass("memU Cloud API key：")
    if mode == "local" and not args.non_interactive and not config_file.read().get("MEMU_DB") and not args.db:
        args.db = input("本地数据库路径 [~/.memu/memu.sqlite3]：").strip() or str(Path.home() / ".memu/memu.sqlite3")
        args.db = str(Path(args.db).expanduser().resolve())
        args.embed_provider = args.embed_provider or input("Embedding provider [openai]：").strip() or "openai"
        args.embed_model = args.embed_model or input("Embedding model [provider 默认]：").strip()
        args.embed_base_url = args.embed_base_url or input("Embedding endpoint [provider 默认]：").strip()
        args.embed_api_key = args.embed_api_key or getpass.getpass("Embedding API key（本地服务可使用占位值）：")
    if mode == "local" and args.db and "://" not in args.db:
        args.db = str(Path(args.db).expanduser().resolve())
    if mode == "local" and not args.db and not config_file.read().get("MEMU_DB"):
        raise Blocked("本地后端需要 --db 指定持久化存储。")


def _inspect(args: argparse.Namespace, state: dict[str, Any]) -> None:
    hooks = _home() / "hooks.json"
    if hooks.is_symlink():
        raise Blocked("hook 配置为符号链接，请先检查其归属和目标。")
    if hooks.exists():
        data = json.loads(hooks.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
            raise Blocked("~/.codex/hooks.json 格式无效；请先修复，安装器不会覆盖。")
    if args.agent and args.new_install and list((_home() / "automations").glob("*/automation.toml")):
        raise Blocked("发现本地自动化任务；请由 Desktop Agent 确认迁移清单。")
    state.setdefault("protected", _snapshot(args.base_dir))


def _backend_hash() -> str | None:
    path = config_file.config_path()
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


async def _integration(args: argparse.Namespace, state: dict[str, Any]) -> None:
    if state.get("backend_checked") != _backend_hash():
        raise Blocked("后端配置已改变，请重新执行第 2 和第 3 阶段。")
    evidence = _migration(args, state)
    state["task_ids"] = sorted(task["id"] for task in evidence["tasks"])
    prepared = cli_prepare.prepare(args.codex)
    if prepared["status"] != "passed":
        raise Blocked("Codex 程序状态发生变化，请重新运行程序准备阶段。")
    state["executable"] = prepared["executable"]
    prompt_hook_install.install(
        prepared["executable"], _home() / "hooks.json", args.cwd, str(args.base_dir), default_home=True
    )
    state["cwd"] = str(args.cwd)
    state["hooks_verified"] = True
    state["backend_sha256"] = _backend_hash()
    state["hooks_sha256"] = hashlib.sha256((_home() / "hooks.json").read_bytes()).hexdigest()


async def _finish(args: argparse.Namespace, state: dict[str, Any]) -> None:
    hooks = _home() / "hooks.json"
    if state.get("cwd") != str(args.cwd):
        raise Blocked("工作目录已改变，请重新执行第 4 阶段。")
    if not state.get("hooks_verified") or not hooks.is_file():
        raise Blocked("请先完成第 4 阶段的双 hook 注册验证。")
    if hashlib.sha256(hooks.read_bytes()).hexdigest() != state.get("hooks_sha256"):
        raise Blocked("hook 配置已改变，请重新执行第 4 阶段验证。")
    if state.get("backend_sha256") != _backend_hash():
        raise Blocked("后端配置已改变，请重新执行第 2 至 4 阶段。")
    evidence = _migration(args, state, deleted=True)
    state["migration_source"] = evidence["source"]
    current = _snapshot(args.base_dir)
    if any(current.get(name) != digest for name, digest in state["protected"].items()):
        raise Blocked("已有工作状态发生变化；请检查 worker 和本地文件，保留现场后再继续。")
    # Read-back trust is required again after a potentially long Desktop handoff.
    await _integration_readback(args, state)
    _check_cleanup()
    if await _command(["remove-instruction", "--dry-run"]):
        raise Blocked("旧检索指令清理预览失败。")
    if await _command(["remove-instruction"]):
        raise Blocked("旧检索指令清理失败。")
    state["complete"] = True


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


async def _integration_readback(args: argparse.Namespace, state: dict[str, Any]) -> None:
    server = prompt_hook_install.AppServer(state["executable"], args.cwd, _home())
    try:
        server.request(
            "initialize",
            {"clientInfo": {"name": "memu-install", "version": "1"}, "capabilities": {"experimentalApi": True}},
        )
        server.notify("initialized")
        listed = server.request("hooks/list", {"cwds": [str(args.cwd)]})
        if any(item.get("errors") or item.get("warnings") for item in listed.get("data", [])):
            raise Blocked("Codex 返回 hook 加载诊断，请重新执行第 4 阶段。")
        config = json.loads((_home() / "hooks.json").read_text(encoding="utf-8"))
        for verb in ("prompt-hook", "memorize-hook"):
            owned = [
                hook
                for group in config["hooks"]["UserPromptSubmit"]
                for hook in group.get("hooks", [])
                if hook.get("type") == "command" and prompt_hook_install._owns_command(hook.get("command", ""), verb)
            ]
            if len(owned) != 1:
                raise Blocked("memU hook 数量不正确，请重新执行第 4 阶段。")
            entries = prompt_hook_install._entries(listed, owned[0]["command"], str(_home() / "hooks.json"))
            if len(entries) != 1 or entries[0].get("trustStatus") != "trusted":
                raise Blocked("Codex 未确认 memU hook 已加载且受信任。")
            if verb == "prompt-hook" and entries[0].get("async") is not True:
                raise Blocked("Codex 未确认异步检索。")
    finally:
        server.close()


async def _stage(stage: int, args: argparse.Namespace, state: dict[str, Any]) -> None:
    if stage == 1:
        _inspect(args, state)
        if not args.agent and args.migration_evidence is None:
            print(
                "请到 Codex Desktop 暂停旧 memU 定时任务，避免它与新的后台记忆同时运行；旧任务迁移交给 Desktop Agent 处理。",
                file=sys.stderr,
            )
    elif stage == 2:
        await _backend(args)
        state["backend_checked"] = _backend_hash()
    elif stage == 3:
        _prepare_host(args, state)
    elif stage == 4:
        await _integration(args, state)
    else:
        await _finish(args, state)


def _prepare_host(args: argparse.Namespace, state: dict[str, Any]) -> None:
    result = cli_prepare.prepare(args.codex, install_missing=args.install_missing)
    if (
        result.get("reason") == "missing"
        and not args.non_interactive
        and not args.install_missing
        and input("是否使用官方安装器补装 Codex？[y/N] ").strip().lower() == "y"
    ):
        result = cli_prepare.prepare(args.codex, install_missing=True)
    if result["status"] == "blocked":
        raise Blocked(result["detail"])
    if result["status"] != "passed":
        raise RuntimeError("Codex CLI 准备失败。")
    args.codex = result["executable"]
    state["executable"] = result["executable"]


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "complete": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise Blocked("安装状态文件无效，请保留现场并检查。")
    if data.get("complete"):
        return {"version": 1, "complete": False}
    return data


def _resume_args(args: argparse.Namespace, state: dict[str, Any]) -> None:
    if args.stage is None and not args.agent and args.migration_evidence is None:
        # A fresh terminal invocation follows terminal policy; single-stage calls resume the saved handoff.
        for key in ("agent", "new_install", "migration_evidence"):
            state.pop(key, None)
    args.agent = args.agent or state.get("agent", False)
    args.new_install = args.new_install or state.get("new_install", False)
    state.update(agent=args.agent, new_install=args.new_install)
    args.codex = args.codex or state.get("executable")
    if args.migration_evidence is None and state.get("migration_evidence"):
        args.migration_evidence = Path(state["migration_evidence"])
    if args.migration_evidence:
        args.migration_evidence = args.migration_evidence.resolve()
        state["migration_evidence"] = str(args.migration_evidence)


async def run(args: argparse.Namespace) -> int:
    args.base_dir = args.base_dir.expanduser().resolve()
    args.cwd = args.cwd.expanduser().resolve()
    args.base_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.base_dir / "install-state.json"
    state: dict[str, Any] = {}
    stage = args.stage or 1
    previous_home = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(_home())
    # Nested commands write diagnostics to stderr in JSON mode; stdout is JSONL progress only.
    output = sys.stdout

    def emit(status: str, **extra: Any) -> None:
        result = {"stage": stage, "title": STAGES[stage - 1], "status": status, **extra}
        print(
            json.dumps(result, ensure_ascii=False)
            if args.json
            else f"[{stage}/5] {STAGES[stage - 1]}：{status} {extra.get('detail', '')}",
            file=output,
            flush=True,
        )

    try:
        with workspace_lock(args.base_dir) as acquired:
            if not acquired:
                emit("blocked", detail="工作目录有活跃 worker 或安装进程，请等待其结束后重试。", complete=False)
                return 2
            state = _load_state(state_path)
            _resume_args(args, state)
            if args.stage and args.stage > 1 and state.get("last_stage", 0) < args.stage - 1:
                emit("blocked", detail="请先执行前置安装阶段。", complete=False)
                return 2
            stages = [args.stage] if args.stage else range(1, args.through_stage + 1)
            for stage in stages:
                emit("started")
                with contextlib.redirect_stdout(sys.stderr if args.json else output):
                    await _stage(stage, args, state)
                state["last_stage"] = stage
                prompt_hook_install._atomic_write(
                    state_path, (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode()
                )
                emit(
                    "passed",
                    complete=state.get("complete", False),
                    migration=state.get("migration_source", "not_checked"),
                )
            if state.get("complete"):
                events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
                events.flush()
            return 0
    except Blocked as exc:
        emit("blocked", detail=str(exc), complete=False)
        return 2
    except (OSError, ValueError, TypeError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        # Keep credential-bearing provider errors out of machine-readable progress/state.
        events.record_cli_error(exc, command="install", host="codex")
        emit("failed", detail=f"{type(exc).__name__}，请检查本地诊断并重跑当前阶段。", complete=False)
        return 1
    finally:
        if previous_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = previous_home


def register(sub: Any) -> None:
    parser = sub.add_parser("install", help="Install Codex memU integration with staged progress and Desktop handoff")
    parser.add_argument(
        "--stage", type=int, choices=range(1, 6), help="Run one stage after its prerequisites have passed"
    )
    parser.add_argument(
        "--through-stage",
        type=int,
        choices=range(1, 6),
        default=5,
        help="Stop after this stage for Agent progress reporting",
    )
    parser.add_argument(
        "--agent", action="store_true", help="Require Desktop migration evidence for Agent-led installation"
    )
    parser.add_argument("--non-interactive", action="store_true", help="Return blockers instead of prompting")
    parser.add_argument("--json", action="store_true", help="Emit JSONL stage progress")
    parser.add_argument("--new-install", action="store_true", help="Confirm no legacy automation migration is required")
    parser.add_argument("--migration-evidence", type=Path, help="Desktop Agent inventory and handoff evidence JSON")
    parser.add_argument("--base-dir", type=Path, default=Path("~/.memu/hosts/codex"))
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex", default=None)
    parser.add_argument("--install-missing", action="store_true")
    parser.add_argument("--backend", choices=("cloud", "local"))
    for name in ("cloud-api-key", "db", "embed-provider", "embed-model", "embed-api-key", "embed-base-url"):
        parser.add_argument("--" + name, default="")
    parser.set_defaults(handler=run)
