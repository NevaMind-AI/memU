"""Select a query using a tool-free request in the Hermes Python environment."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Any

from memu.hosts import query_extraction


def select_query(
    prompt: str, trace: dict[str, Any], *, python: str | None, python_paths: list[str] | None = None
) -> str:
    return query_extraction.select_query(
        prompt, trace, lambda text: _extract(text, python=python, python_paths=python_paths)
    )


def _extract(prompt: str, *, python: str | None, python_paths: list[str] | None = None) -> str:
    if not python:
        raise ValueError("Hermes Python runtime was not supplied by the plugin")  # noqa: TRY003
    source = files("memu.hosts.hermes").joinpath("query_worker.py").read_text(encoding="utf-8")
    env = {**os.environ, "MEMU_BRIDGING_RUN": "1", "PYTHONIOENCODING": "utf-8"}
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="memu-query-") as directory:
        request = Path(directory) / "request.txt"
        request.write_text(query_extraction.extraction_instruction(prompt), encoding="utf-8")
        output = query_extraction.run_extraction(
            [python, "-c", source, str(request), json.dumps(python_paths)],
            b"",
            Path(directory),
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=env,
        )
    return query_extraction.validate_query(json.loads(output.decode("utf-8")))
