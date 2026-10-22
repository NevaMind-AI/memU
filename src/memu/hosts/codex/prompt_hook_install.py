"""Register and trust memU's Codex prompt hook through app-server."""

from __future__ import annotations

import argparse
import json
import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


class AppServer:
    def __init__(self, executable: str, cwd: Path) -> None:
        self.process = subprocess.Popen(  # noqa: S603
            [executable, "app-server", "--stdio"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.request_id = 0
        self.lines: queue.Queue[str | None] = queue.Queue()
        if self.process.stdout is None:
            raise RuntimeError("Codex app-server stdout is unavailable")  # noqa: TRY003
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        if self.process.stdout is None:
            raise RuntimeError("Codex app-server stdout is unavailable")  # noqa: TRY003
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.request_id += 1
        request_id = self.request_id
        if self.process.stdin is None:
            raise RuntimeError("Codex app-server stdin is unavailable")  # noqa: TRY003
        self.process.stdin.write(json.dumps({"id": request_id, "method": method, "params": params or {}}) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 30
        while True:
            try:
                line = self.lines.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise TimeoutError(f"Timed out waiting for Codex app-server {method}") from exc  # noqa: TRY003
            if line is None:
                raise RuntimeError(f"Codex app-server exited while handling {method}")  # noqa: TRY003
            response = json.loads(line)

            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise RuntimeError(f"Codex app-server {method} failed: {response['error']}")  # noqa: TRY003
            result = response.get("result", {})
            if not isinstance(result, dict):
                raise RuntimeError(f"Unexpected Codex app-server result for {method}")  # noqa: TRY003
            return result

    def notify(self, method: str) -> None:
        if self.process.stdin is None:
            raise RuntimeError("Codex app-server stdin is unavailable")  # noqa: TRY003
        self.process.stdin.write(json.dumps({"method": method, "params": {}}) + "\n")
        self.process.stdin.flush()

    def close(self) -> None:
        if self.process.poll() is None:
            if self.process.stdin:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)


def _atomic_write(path: Path, data: bytes) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(name, path)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def _entries(value: Any, command: str, source: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("command") == command and value.get("sourcePath", "").casefold() == source.casefold():
            found.append(value)
        for child in value.values():
            found.extend(_entries(child, command, source))
    elif isinstance(value, list):
        for child in value:
            found.extend(_entries(child, command, source))
    return found


def _command() -> str:
    argv = [str(Path(sys.argv[0]).resolve()), "prompt-hook"]
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def _definition(groups: list[dict[str, Any]], command: str) -> None:
    matches = [
        hook
        for group in groups
        for hook in group.get("hooks", [])
        if hook.get("type") == "command"
        and "prompt-hook" in hook.get("command", "")
        and Path(hook.get("command", "").split(" prompt-hook", 1)[0].strip("\\\"' "))
        .name.casefold()
        .startswith("memu-codex")
    ]
    definition = {
        "type": "command",
        "command": command,
        "timeout": 50,
        "additionalContextLimit": 0,
        "statusMessage": "Retrieving memU memory",
    }
    if matches:
        matches[0].update(definition)
        for duplicate in matches[1:]:
            for group in groups:
                if duplicate in group.get("hooks", []):
                    group["hooks"].remove(duplicate)
    else:
        groups.append({"hooks": [definition]})


def install(codex: str, hooks_file: Path, cwd: Path) -> None:
    command = _command()
    if hooks_file.exists() and not hooks_file.is_file():
        raise FileNotFoundError(f"Codex hooks path is not a file: {hooks_file}")  # noqa: TRY003

    server = AppServer(codex, cwd)
    try:
        server.request(
            "initialize",
            {"clientInfo": {"name": "memu-install", "version": "1"}, "capabilities": {"experimentalApi": True}},
        )
        server.notify("initialized")
        server.request("hooks/list", {"cwds": [str(cwd)]})

        if hooks_file.exists():
            original = hooks_file.read_bytes()
        else:
            hooks_file.parent.mkdir(parents=True, exist_ok=True)
            original = b"{}"
        config = json.loads(original.decode("utf-8-sig"))
        hooks = config.setdefault("hooks", {})
        groups = hooks.setdefault("UserPromptSubmit", [])
        if not isinstance(groups, list) or any(not isinstance(group, dict) for group in groups):
            raise ValueError("hooks.UserPromptSubmit must be an array of hook groups")  # noqa: TRY003
        _definition(groups, command)

        backup = hooks_file.with_name("hooks.json.memu-backup")
        if not backup.exists() and hooks_file.exists():
            backup.write_bytes(original)
        _atomic_write(hooks_file, (json.dumps(config, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))

        listed = server.request("hooks/list", {"cwds": [str(cwd)]})
        data = listed.get("data", [])
        if any(item.get("errors") or item.get("warnings") for item in data):
            raise RuntimeError("Codex reported hook loading warnings or errors")  # noqa: TRY003
        entries = _entries(listed, command, str(hooks_file))
        if len(entries) != 1:
            raise RuntimeError(f"Expected one loaded memU hook, found {len(entries)}; check Codex hooks/list warnings")  # noqa: TRY003
        entry = entries[0]
        key, fingerprint = entry.get("key"), entry.get("currentHash")
        if not key or not fingerprint:
            raise RuntimeError("Codex did not return hook key and currentHash")  # noqa: TRY003
        server.request(
            "config/value/write",
            {
                "keyPath": "hooks.state." + json.dumps(key) + ".trusted_hash",
                "value": fingerprint,
                "mergeStrategy": "upsert",
            },
        )
        verified = _entries(server.request("hooks/list", {"cwds": [str(cwd)]}), command, str(hooks_file))
        if len(verified) != 1 or verified[0].get("trustStatus") != "trusted":
            raise RuntimeError("Codex did not confirm the memU prompt hook as trusted")  # noqa: TRY003
        print("Registered one memU UserPromptSubmit hook; Codex reports it trusted.")
        print(f"Backup: {backup}")
    finally:
        server.close()


def register(sub: Any) -> None:
    parser = sub.add_parser("install-prompt-hook", help="Register and trust the Codex retrieval hook")
    parser.add_argument("--codex", default=shutil.which("codex"), help="Codex CLI executable (default: PATH)")
    parser.add_argument("--hooks-file", type=Path, default=Path("~/.codex/hooks.json").expanduser())
    parser.add_argument("--cwd", type=Path, default=Path.cwd())

    async def handler(args: argparse.Namespace) -> int:
        if not args.codex:
            raise FileNotFoundError("Codex CLI is not on PATH; pass --codex with its executable path")  # noqa: TRY003
        install(args.codex, args.hooks_file.expanduser().resolve(), args.cwd.resolve())
        return 0

    parser.set_defaults(handler=handler)
