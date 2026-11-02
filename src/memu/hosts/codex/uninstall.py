"""Remove the two memU Submit handlers from the default Codex home."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from memu.hosts.codex import cli_prepare
from memu.hosts.codex import prompt_hook_install as hooks


def _owned(hook: dict[str, Any]) -> bool:
    return hook.get("type") == "command" and any(
        hooks._owns_command(hook.get("command", ""), verb) for verb in ("prompt-hook", "memorize-hook")
    )


def _remove_definitions(config: dict[str, Any]) -> tuple[list[str], set[str]]:
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise TypeError("Hook configuration must contain a hooks object")  # noqa: TRY003
    groups = config.get("hooks", {}).get("UserPromptSubmit", [])
    if not isinstance(groups, list) or any(
        not isinstance(group, dict) or not isinstance(group.get("hooks", []), list) for group in groups
    ):
        raise ValueError("hooks.UserPromptSubmit must be an array of hook groups")  # noqa: TRY003
    removed = []
    remaining = set()
    for group in groups:
        kept = []
        for hook in group.get("hooks", []):
            if not isinstance(hook, dict):
                raise TypeError("Hook definitions must be objects")  # noqa: TRY003
            if _owned(hook):
                removed.append(hook["command"])
            else:
                kept.append(hook)
                if hook.get("type") == "command":
                    remaining.add(hook["command"])
        if "hooks" in group:
            group["hooks"] = kept
    return removed, remaining


def uninstall(codex: str | None, cwd: Path) -> int:
    """Remove owned definitions and preserve previously trusted foreign handlers."""
    path = Path.home() / ".codex/hooks.json"
    if path.is_symlink():
        raise ValueError("Inspect the hooks.json symlink before uninstalling")  # noqa: TRY003
    if not path.exists():
        return 0
    original = path.read_bytes()
    config = json.loads(original.decode("utf-8-sig"))
    removed, remaining = _remove_definitions(config)
    if not removed:
        return 0
    prepared = cli_prepare.prepare(codex)
    if prepared["status"] != "passed":
        return _offline_uninstall(path, original, config, removed)
    server = hooks.AppServer(prepared["executable"], cwd, path.parent)
    try:
        server.request(
            "initialize",
            {"clientInfo": {"name": "memu-uninstall", "version": "1"}, "capabilities": {"experimentalApi": True}},
        )
        server.notify("initialized")
        before = server.request("hooks/list", {"cwds": [str(cwd)]})
        backup = path.with_name("hooks.json.memu-uninstall-backup")
        if not backup.exists():
            hooks._atomic_write(backup, original)
        if path.read_bytes() != original:
            raise RuntimeError("Hook configuration changed during uninstall; retry")  # noqa: TRY003
        updated = (json.dumps(config, ensure_ascii=True, indent=2) + "\n").encode()
        hooks._atomic_write(path, updated)
        try:
            listed = server.request("hooks/list", {"cwds": [str(cwd)]})
            if any(hooks._entries(listed, command, str(path)) for command in removed):
                raise RuntimeError("Codex still reports a removed memU hook")  # noqa: TRY003, TRY301
            updates = _trust_updates(before, listed, remaining, path)
        except Exception:
            if path.read_bytes() == updated:
                hooks._atomic_write(path, original)
            raise
        # Trust updates happen after validation; keep the verified removal if an API write fails.
        _apply_trust(server, updates, path, cwd)
    finally:
        server.close()
    return len(removed)


def _offline_trust(original: bytes, path: Path) -> dict[str, str | None]:
    """Map Codex's positional trust keys to surviving definitions."""
    config = json.loads(original.decode("utf-8-sig"))
    updates: dict[str, str | None] = {}
    for i, group in enumerate(config.get("hooks", {}).get("UserPromptSubmit", [])):
        index = 0
        for j, hook in enumerate(group.get("hooks", [])):
            old = f"{path}:user_prompt_submit:{i}:{j}"
            if _owned(hook):
                updates[old] = None
            else:
                updates[old] = f"{path}:user_prompt_submit:{i}:{index}"
                index += 1
    return updates


def _remap_trust(data: bytes, updates: dict[str, str | None]) -> bytes:
    """Edit only Codex-generated trust tables, preserving surrounding TOML verbatim."""
    source = data.decode("utf-8-sig")
    state = tomllib.loads(source).get("hooks", {}).get("state", {})
    affected = {key for key in state if key in updates and updates[key] != key}
    if not affected:
        return data
    # Codex writes each approval as its own [hooks.state."key"] table.
    sections = re.split(r"(?m)^(?=[ \t]*\[)", source)
    found = set()
    result = []
    for section in sections:
        header, separator, body = section.partition("\n")
        try:
            parsed = tomllib.loads(header.rstrip("\r")).get("hooks", {}).get("state", {})
        except tomllib.TOMLDecodeError:
            parsed = {}
        keys = affected.intersection(parsed)
        if not keys:
            result.append(section)
            continue
        key = keys.pop()
        if len(parsed) != 1 or parsed[key]:
            raise ValueError("Unsupported hook trust table; preserve config.toml and inspect its layout")  # noqa: TRY003
        found.add(key)
        target = updates[key]
        if target is not None:
            ending = "\r\n" if header.endswith("\r") else separator
            result.append(f"[hooks.state.{json.dumps(target, ensure_ascii=True)}]" + ending + body)
    if found != affected:
        raise ValueError("Hook trust uses a custom TOML layout; preserve config.toml and inspect it before removal")  # noqa: TRY003
    updated = "".join(result)
    tomllib.loads(updated)
    return (b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8")


def _offline_uninstall(path: Path, original: bytes, config: dict[str, Any], removed: list[str]) -> int:
    settings = path.with_name("config.toml")
    if settings.is_symlink():
        raise ValueError("Inspect the config.toml symlink before uninstalling")  # noqa: TRY003
    previous = settings.read_bytes() if settings.exists() else None
    trust = _remap_trust(previous, _offline_trust(original, path)) if previous is not None else None
    updated = (json.dumps(config, ensure_ascii=True, indent=2) + "\n").encode()
    for target, data in ((path, original), (settings, previous)):
        backup = target.with_name(target.name + ".memu-uninstall-backup")
        if data is not None and not backup.exists():
            hooks._atomic_write(backup, data)
    if path.read_bytes() != original or (settings.read_bytes() if settings.exists() else None) != previous:
        raise RuntimeError("Codex configuration changed during uninstall; retry")  # noqa: TRY003
    # Remove definitions first; a failed trust write restores this change when still owned.
    hooks._atomic_write(path, updated)
    try:
        if trust is not None and trust != previous:
            if settings.read_bytes() != previous:
                raise RuntimeError("Codex trust configuration changed during uninstall")  # noqa: TRY003, TRY301
            hooks._atomic_write(settings, trust)
        if path.read_bytes() != updated:
            raise RuntimeError("Hook configuration changed during uninstall")  # noqa: TRY003, TRY301
    except Exception:
        if path.read_bytes() == updated:
            hooks._atomic_write(path, original)
        raise
    return len(removed)


def _trust_updates(
    before: dict[str, Any], after: dict[str, Any], commands: set[str], path: Path
) -> list[tuple[str, dict[str, Any]]]:
    updates = []
    for command in commands:
        previous = hooks._entries(before, command, str(path))
        current = hooks._entries(after, command, str(path))
        if [entry.get("currentHash") for entry in previous] != [entry.get("currentHash") for entry in current]:
            raise RuntimeError("A third-party hook changed during uninstall")  # noqa: TRY003
        for old, new in zip(previous, current, strict=True):
            if old.get("trustStatus") != "trusted" and new.get("trustStatus") == "trusted":
                raise RuntimeError("Uninstall would change an untrusted hook's approval")  # noqa: TRY003
            if old.get("trustStatus") == "trusted" and new.get("trustStatus") != "trusted":
                updates.append((command, new))
    return updates


def _apply_trust(server: hooks.AppServer, updates: list[tuple[str, dict[str, Any]]], path: Path, cwd: Path) -> None:
    for command, entry in updates:
        try:
            hooks._trust_entry(server, entry)
        except Exception as exc:
            raise RuntimeError("Hooks removed, but restoring third-party trust failed; inspect the backup") from exc  # noqa: TRY003
        verified = hooks._entries(server.request("hooks/list", {"cwds": [str(cwd)]}), command, str(path))
        if not any(hook.get("key") == entry.get("key") and hook.get("trustStatus") == "trusted" for hook in verified):
            raise RuntimeError("Hooks removed, but Codex did not preserve third-party hook trust; inspect the backup")  # noqa: TRY003


def register(sub: Any) -> None:
    parser = sub.add_parser("uninstall", help="Unregister the memU retrieval and memorization hooks")
    parser.add_argument("--codex", default=None, help="Codex CLI executable")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Working directory for Codex read-back")

    async def handler(args: argparse.Namespace) -> int:
        print("\n🧹 memU Uninstaller", flush=True)
        removed = uninstall(args.codex, args.cwd.expanduser().resolve())
        print(f"✅ Removed {removed} memU hook(s)." if removed else "✅ No memU hooks to remove.")
        print("💡 Memory, backend configuration and other integrations are preserved.")
        return 0

    parser.set_defaults(handler=handler)
