"""Read-only diagnostics for the Codex executable and registered memU hooks."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from memu.hosts.codex import cli_prepare, prompt_hook_install


def check() -> int:
    """Check local integration definitions; installation owns repairs and trust verification."""
    failed = False
    try:
        executable = cli_prepare.find_executable()
        result = cli_prepare.prepare(str(executable))
        if result["status"] != "passed":
            raise ValueError(result["detail"])  # noqa: TRY301
        print(f"codex-cli ok ({result['version']}; {executable})")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"codex-cli failed: {exc}")
        failed = True

    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    path = home / "hooks.json"
    try:
        definitions = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
        hooks = definitions.get("hooks", {}).get("UserPromptSubmit", [])
        if not isinstance(hooks, list):
            raise TypeError("hooks.UserPromptSubmit must be an array")  # noqa: TRY003, TRY301
        entries = [hook for group in hooks for hook in group.get("hooks", [])]
        for subcommand in ("prompt-hook", "memorize-hook"):
            problem = _hook_problem(entries, subcommand)
            print(f"{subcommand} {problem or 'ok (local definition)'}")
            failed |= bool(problem)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"hooks failed: {path}: {exc}")
        failed = True
    if failed:
        print("hint: run `memu-codex install` to repair or update the Codex integration.")
    return int(failed)


def _hook_problem(entries: list[dict[str, Any]], subcommand: str) -> str:
    matches = [
        hook
        for hook in entries
        if hook.get("type") == "command" and prompt_hook_install._owns_command(hook.get("command", ""), subcommand)
    ]
    if not matches:
        return "missing"
    if len(matches) != 1:
        return "outdated (duplicate definitions; update recommended)"
    hook = matches[0]
    # Reuse the installer's current definition as the compatibility baseline.
    expected: list[dict[str, Any]] = []
    prompt_hook_install._definition(expected, hook["command"], subcommand)
    definition = expected[0]["hooks"][0]
    if any(hook.get(key) != value for key, value in definition.items()) or (
        subcommand == "memorize-hook" and hook.get("async") is True
    ):
        return "outdated (definition differs from this memU version; update recommended)"
    if subcommand == "memorize-hook" and re.search(r"(?:^|\s)--agent(?:\s|=)", hook["command"]):
        return "outdated (fixed CLI path; update recommended)"
    return ""
