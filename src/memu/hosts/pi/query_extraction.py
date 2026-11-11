"""Extract memory queries with an isolated, tool-free pi request."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from memu.hosts import query_extraction


def select_query(prompt: str, trace: dict[str, Any], *, provider: str | None = None, model: str | None = None) -> str:
    return query_extraction.select_query(prompt, trace, lambda text: _extract(text, provider=provider, model=model))


def _extract(prompt: str, *, provider: str | None = None, model: str | None = None) -> str:
    binary = shutil.which("pi")
    if not binary:
        raise FileNotFoundError("pi is not on PATH")  # noqa: TRY003
    argv = [
        binary,
        "-p",
        "--no-session",
        "--offline",
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-context-files",
        "--no-tools",
        "--system-prompt",
        "Extract the query only. Do not use tools. Return a JSON object containing a nonempty query string.",
    ]
    for name, value in (("provider", provider), ("model", model)):
        if value:
            argv.extend([f"--{name}", value])
    # A pipe preserves multiline prompts through Windows npm command wrappers.
    with tempfile.TemporaryDirectory(prefix="memu-query-") as directory:
        output = query_extraction.run_extraction(
            argv,
            query_extraction.extraction_instruction(prompt).encode("utf-8"),
            Path(directory),
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env={**os.environ, "MEMU_BRIDGING_RUN": "1"},
        )
    return query_extraction.validate_query(json.loads(output.decode("utf-8")))
