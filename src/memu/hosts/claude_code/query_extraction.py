"""Extract memory queries with an isolated standalone Claude request."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from memu.hosts import query_extraction
from memu.hosts.claude_code import cli_prepare


def select_query(prompt: str, trace: dict[str, Any]) -> str:
    return query_extraction.select_query(prompt, trace, _extract)


def _extract(prompt: str) -> str:
    binary = str(cli_prepare.find_executable())
    env = {**cli_prepare.standalone_env(), "MEMU_BRIDGING_RUN": "1", "MEMU_CLAUDE_MEMORIZE": "1"}
    with tempfile.TemporaryDirectory(prefix="memu-query-") as directory:
        output = query_extraction.run_extraction(
            [
                binary,
                "-p",
                "--output-format",
                "json",
                "--no-session-persistence",
                "--tools",
                "",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--settings",
                '{"disableAllHooks":true}',
                "--system-prompt",
                "Extract the query only. Do not use tools.",
            ],
            query_extraction.extraction_instruction(prompt).encode("utf-8"),
            Path(directory),
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=env,
        )
    value = json.loads(output.decode("utf-8"))
    result = value.get("result") if isinstance(value, dict) else None
    if not isinstance(result, str) or value.get("is_error"):
        raise ValueError("Claude query extraction failed")  # noqa: TRY003
    return query_extraction.validate_query(json.loads(result))
