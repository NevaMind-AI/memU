"""Extract bounded memory queries through the host's ephemeral Codex CLI."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from memu.hosts import query_extraction
from memu.hosts.codex import cli_prepare

EXTRACT_THRESHOLD = query_extraction.EXTRACT_THRESHOLD
EXTRACT_TIMEOUT = query_extraction.EXTRACT_TIMEOUT


def select_query(prompt: str, trace: dict[str, Any]) -> str:
    return query_extraction.select_query(prompt, trace, _extract)


def _https_options() -> list[str]:
    """One-shot extraction should not spend its deadline retrying WebSockets."""
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    config = home / "config.toml"
    values = tomllib.loads(config.read_text(encoding="utf-8-sig")) if config.is_file() else {}
    providers = [
        name
        for name, settings in values.get("model_providers", {}).items()
        if settings.get("supports_websockets") is True and re.fullmatch(r"[A-Za-z0-9_-]+", name)
    ]
    return [
        option
        for provider in sorted(providers)
        for option in ("-c", f"model_providers.{provider}.supports_websockets=false")
    ]


def _extract(prompt: str) -> str:
    binary = str(cli_prepare.find_executable())
    with tempfile.TemporaryDirectory(prefix="memu-query-") as directory:
        base = Path(directory)
        schema = base / "schema.json"
        output = base / "query.json"
        schema.write_text(
            json.dumps({
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            }),
            encoding="utf-8",
        )
        instruction = query_extraction.extraction_instruction(prompt)
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW
        _run(
            [
                binary,
                "exec",
                *_https_options(),
                "--ephemeral",
                "--disable",
                "hooks",
                "--ignore-rules",
                "--skip-git-repo-check",
                "-s",
                "read-only",
                "-c",
                'model_reasoning_effort="low"',
                "-c",
                "notify=[]",
                "--output-schema",
                str(schema),
                "-o",
                str(output),
                "-",
            ],
            instruction.encode("utf-8"),
            base,
            flags,
        )
        value = json.loads(output.read_text(encoding="utf-8"))
        return query_extraction.validate_query(value)


def _run(argv: list[str], source: bytes, cwd: Path, flags: int) -> None:
    query_extraction.run_extraction(
        argv,
        source,
        cwd,
        flags,
        env={**os.environ, "MEMU_BRIDGING_RUN": "1", "MEMU_CODEX_MEMORIZE": "1"},
        timeout=EXTRACT_TIMEOUT,
    )
