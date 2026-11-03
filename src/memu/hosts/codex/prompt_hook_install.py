"""Register and trust memU's Codex prompt hook through app-server."""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from memu.hosts.bridging import Layout
from memu.hosts.codex import cli_prepare


class AppServer:
    def __init__(self, executable: str, cwd: Path, codex_home: Path) -> None:
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        self.process = subprocess.Popen(  # noqa: S603
            [executable, "app-server", "--stdio"],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # Drain diagnostics concurrently so a verbose server cannot block its RPC responses.
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.request_id = 0
        self.lines: queue.Queue[str | None] = queue.Queue()
        if self.process.stdout is None:
            raise RuntimeError("Codex app-server stdout is unavailable")  # noqa: TRY003
        threading.Thread(target=self._read, daemon=True).start()
        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stderr_thread.start()

    def _read_stderr(self) -> None:
        if self.process.stderr is None:
            return
        for line in self.process.stderr:
            # Codex logs this nonfatal configuration advisory at ERROR severity.
            plain = re.sub(r"\x1b\[[0-9;]*m", "", line)
            advisory = (
                r"Codex is ignoring \d+ unrecognized configuration settings?\. "
                r"Check for typos or deprecated settings\."
            )
            if re.fullmatch(r"(?:\S+\s+)?ERROR codex_app_server: " + advisory + r"\s*", plain):
                line = plain.replace("ERROR codex_app_server:", "WARN codex_app_server:", 1)
            elif plain.lstrip().startswith("{"):
                try:
                    diagnostic = json.loads(plain)
                except ValueError:
                    diagnostic = None
                if (
                    isinstance(diagnostic, dict)
                    and diagnostic.get("level") == "ERROR"
                    and diagnostic.get("target") == "codex_app_server"
                    and isinstance(diagnostic.get("fields"), dict)
                    and isinstance(message := diagnostic["fields"].get("message"), str)
                    and re.match(advisory + r"(?:\n|$)", message)
                ):
                    diagnostic["level"] = "WARN"
                    line = json.dumps(diagnostic, ensure_ascii=False) + "\n"
            print(line, end="", file=sys.stderr, flush=True)

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
                raise TypeError(f"Unexpected Codex app-server result for {method}")  # noqa: TRY003
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
        self.stderr_thread.join(timeout=5)


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


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'" if sys.platform == "win32" else shlex.quote(value)


def _command(subcommand: str = "prompt-hook") -> str:
    executable = str(Path(sys.argv[0]).resolve())
    if sys.platform == "win32":
        return "& " + _quote(executable) + " " + subcommand
    return shlex.join([executable, subcommand])


def _owns_command(command: str, subcommand: str = "prompt-hook") -> bool:
    value = r"""(?:"[^"]*"|'(?:[^']|'')*'|[^\s'"&;|]+)"""
    options = r"(?:\s+--base-dir\s+" + value + r")?(?:\s+--default-home)?"
    if subcommand == "memorize-hook":
        options = r"(?:\s+--(?:agent|base-dir|session-dir)\s+" + value + r"|\s+--default-home)*"
    match = re.fullmatch(
        r"""\s*(?:&\s+)?(?:"([^"]+)"|'((?:[^']|'')+)'|([^\s'"&;|]+))\s+""" + re.escape(subcommand) + options + r"\s*",
        command,
    )
    if match is None:
        return False
    executable = next(part for part in match.groups() if part is not None).replace("''", "'")
    return executable.replace("\\", "/").rsplit("/", 1)[-1].casefold() in {"memu-codex", "memu-codex.exe"}


def _definition(groups: list[dict[str, Any]], command: str, subcommand: str = "prompt-hook") -> None:
    matches = [
        hook
        for group in groups
        for hook in group.get("hooks", [])
        if hook.get("type") == "command" and _owns_command(hook.get("command", ""), subcommand)
    ]
    definition = {
        "type": "command",
        "command": command,
        "timeout": 50 if subcommand == "prompt-hook" else 10,
        "additionalContextLimit": 0,
        "statusMessage": "Retrieving memU memory" if subcommand == "prompt-hook" else "Starting memU memory processing",
    }
    if subcommand == "prompt-hook":
        definition["async"] = True
    if matches:
        matches[0].update(definition)
        for duplicate in matches[1:]:
            for group in groups:
                if duplicate in group.get("hooks", []):
                    group["hooks"].remove(duplicate)
    else:
        groups.append({"hooks": [definition]})


def _trust(server: AppServer, listed: dict[str, Any], command: str, hooks_file: Path, cwd: Path) -> None:
    entries = _entries(listed, command, str(hooks_file))
    if len(entries) != 1:
        raise RuntimeError(  # noqa: TRY003
            f"Expected one loaded memU hook, found {len(entries)}; check Codex hooks/list warnings"
        )
    entry = entries[0]
    _trust_entry(server, entry)
    verified = _entries(server.request("hooks/list", {"cwds": [str(cwd)]}), command, str(hooks_file))
    if len(verified) != 1 or verified[0].get("trustStatus") != "trusted":
        raise RuntimeError("Codex did not confirm the memU prompt hook as trusted")  # noqa: TRY003


def _trust_entry(server: AppServer, entry: dict[str, Any]) -> None:
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


def install(
    codex: str, hooks_file: Path, cwd: Path, base_dir: str | None = None, *, default_home: bool = False
) -> None:
    codex = str(Path(shutil.which(codex) or codex).resolve())
    base = Layout.default("codex", base_dir or "~/.memu/hosts/codex").base.resolve()
    command = _command() + " --base-dir " + _quote(str(base))
    memorize = (
        _command("memorize-hook")
        + " --base-dir "
        + _quote(str(base))
        + " --session-dir "
        + _quote(str(hooks_file.parent / "sessions"))
    )
    if default_home:
        command += " --default-home"
        memorize += " --default-home"
    if hooks_file.exists() and not hooks_file.is_file():
        raise FileNotFoundError(f"Codex hooks path is not a file: {hooks_file}")  # noqa: TRY003

    if hooks_file.name != "hooks.json":
        raise ValueError("Codex loads hooks.json from its home; --hooks-file must name hooks.json")  # noqa: TRY003
    server = AppServer(codex, cwd, hooks_file.parent)
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
        _definition(groups, memorize, "memorize-hook")

        backup = hooks_file.with_name("hooks.json.memu-backup")
        if not backup.exists() and hooks_file.exists():
            backup.write_bytes(original)
        _atomic_write(hooks_file, (json.dumps(config, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))

        listed = server.request("hooks/list", {"cwds": [str(cwd)]})
        data = listed.get("data", [])
        if any(item.get("errors") or item.get("warnings") for item in data):
            raise RuntimeError("Codex reported hook loading warnings or errors")  # noqa: TRY003
        retrieval = _entries(listed, command, str(hooks_file))
        if len(retrieval) == 1 and retrieval[0].get("async") is not True:
            raise RuntimeError(  # noqa: TRY003
                "Codex did not confirm asynchronous retrieval; update Codex and retry install-prompt-hook"
            )
        for registered_command in (command, memorize):
            _trust(server, listed, registered_command, hooks_file, cwd)
        print("Registered asynchronous retrieval and background memorization hooks; Codex reports both trusted.")
        print(f"Backup: {backup}")
    finally:
        server.close()


def register(sub: Any) -> None:
    parser = sub.add_parser("install-prompt-hook", help="Register and trust Codex retrieval and memorization hooks")
    parser.add_argument("--codex", default=None, help="Standalone Codex CLI executable")
    codex_home = Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser()
    parser.add_argument("--hooks-file", type=Path, default=codex_home / "hooks.json")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--base-dir", default=None)

    async def handler(args: argparse.Namespace) -> int:
        prepared = cli_prepare.prepare(args.codex)
        if prepared["status"] != "passed":
            raise RuntimeError(prepared["detail"])
        install(prepared["executable"], args.hooks_file.expanduser().resolve(), args.cwd.resolve(), args.base_dir)
        return 0

    parser.set_defaults(handler=handler)
