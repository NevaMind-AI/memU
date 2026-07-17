"""Both CLI entries force UTF-8 stdio before anything prints.

Piped stdio on Windows falls back to the ANSI code page (gbk on zh-CN, cp1252
on en-US), which cannot encode the packaged guides' ✅ or stored memory content
— and agents read every command through a pipe. These tests hand each entry the
exact stream a Chinese-locale Windows pipe provides and expect UTF-8 bytes out;
like the rest of the CLI tests, they never construct a MemoryService.
"""

from __future__ import annotations

import io
import sys

import pytest

from memu.cli import main
from memu.hosts.claude_code.cli import SPEC
from memu.hosts.host_cli import run


def _gbk_pipe() -> tuple[io.TextIOWrapper, io.BytesIO]:
    buffer = io.BytesIO()
    return io.TextIOWrapper(buffer, encoding="gbk"), buffer


def test_host_docs_install_survives_gbk_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without the entry-point reconfigure this is the field failure: the guide's
    # first ✅ raises UnicodeEncodeError and the agent gets zero lines of it.
    stdout, buffer = _gbk_pipe()
    monkeypatch.setattr(sys, "stdout", stdout)
    assert run(SPEC, ["docs", "install"]) == 0
    stdout.flush()
    assert "✅" in buffer.getvalue().decode("utf-8")


def test_memu_entry_reconfigures_both_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout, _ = _gbk_pipe()
    stderr, err_buffer = _gbk_pipe()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    # The no-service error path: parses argv, prints the error, exits 2.
    assert main(["commit", "/definitely/not/a/payload.json"]) == 2
    assert stdout.encoding == "utf-8"
    assert stderr.encoding == "utf-8"
    stderr.flush()
    assert "no such file" in err_buffer.getvalue().decode("utf-8")
