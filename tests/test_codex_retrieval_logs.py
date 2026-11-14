"""Retrieval logs contain one complete, readable trace per invocation."""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest

from memu.hosts.codex import prompt_hook
from memu.hosts.hooks import worker


def invoke(base: Path) -> int:
    return asyncio.run(prompt_hook._cmd_prompt_hook(argparse.Namespace(base_dir=str(base))))


def test_same_clock_and_process_do_not_overwrite_or_skip_retrieval(tmp_path, monkeypatch):
    class FixedClock:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 2)

    monkeypatch.setattr(worker, "datetime", FixedClock)
    calls: list[dict[str, object]] = []

    def retrieve(trace):
        trace.update(status="empty_result", query="query", invocation=len(calls))
        calls.append(trace)

    monkeypatch.setattr(prompt_hook, "_retrieve", retrieve)
    old = tmp_path / "log/hooks/retrieve/2025-01-01_00-00-00.000000-1.log"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"old diagnostic\n")
    for _ in range(3):
        assert invoke(tmp_path) == 0
    logs = list(old.parent.glob("*.json"))
    assert len(calls) == len(logs) == 3
    assert {json.loads(p.read_text(encoding="utf-8"))["invocation"] for p in logs} == {0, 1, 2}
    assert old.read_bytes() == b"old diagnostic\n"
    assert list(old.parent.glob("*.log")) == [old]


@pytest.mark.parametrize("event", ["{", "[]", '{"hook_event_name":"other"}'])
def test_invalid_event_still_has_one_failed_trace(tmp_path, monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(event))
    assert invoke(tmp_path) == 0
    logs = list((tmp_path / "log/hooks/retrieve").iterdir())
    assert len(logs) == 1 and logs[0].suffix == ".json"
    text = logs[0].read_text(encoding="utf-8")
    trace = json.loads(text)
    assert trace["status"] == "failed" and trace["error"]
    assert trace["elapsed_ms"] >= 0
    assert text == json.dumps(trace, ensure_ascii=False, indent=2) + "\n"


def test_log_open_failure_keeps_existing_skip_behavior(tmp_path, monkeypatch, capsys):
    original = Path.open
    calls: list[dict[str, object]] = []

    def open_log(path, *args, **kwargs):
        if path.parent == tmp_path / "log/hooks/retrieve":
            raise PermissionError("fixture log unavailable")  # noqa: TRY003
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_log)
    monkeypatch.setattr(prompt_hook, "_retrieve", lambda trace: calls.append(trace))
    assert invoke(tmp_path) == 0
    output = capsys.readouterr()
    assert not calls and not output.out
    assert "prompt hook log failed" in output.err


def test_final_log_write_failure_does_not_retract_delivered_context(tmp_path, monkeypatch, capsys):
    class UnwritableLog(io.StringIO):
        def write(self, text):
            raise OSError("fixture write failed")  # noqa: TRY003

    original = Path.open

    def open_log(path, *args, **kwargs):
        if path.parent == tmp_path / "log/hooks/retrieve":
            return UnwritableLog()
        return original(path, *args, **kwargs)

    def retrieve(trace):
        trace.update(status="context_returned")
        print('{"hookSpecificOutput":{"additionalContext":"delivered"}}')

    monkeypatch.setattr(Path, "open", open_log)
    monkeypatch.setattr(prompt_hook, "_retrieve", retrieve)
    assert invoke(tmp_path) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["hookSpecificOutput"]["additionalContext"] == "delivered"
    assert "prompt hook log failed" in output.err


def test_concurrent_native_processes_keep_separate_unicode_traces(tmp_path):
    script = """
import argparse, asyncio, json, subprocess, sys
from memu.hosts.codex import prompt_hook
def retrieve(argv, **kwargs):
    return subprocess.CompletedProcess(argv, 0, json.dumps({"hits":[{"text":"记忆 😀"}],"resources":[]}).encode(), b"")
prompt_hook.subprocess.run = retrieve
asyncio.run(prompt_hook._cmd_prompt_hook(argparse.Namespace(base_dir=sys.argv[1])))
"""
    environment = {**os.environ, "PYTHONPATH": str(Path(prompt_hook.__file__).parents[3]), "PYTHONUTF8": "1"}

    def run(index):
        event = {"hook_event_name": "UserPromptSubmit", "session_id": str(index), "prompt": f"查询 {index}"}
        return subprocess.run(  # noqa: S603 -- fixed local fixture, fake retrieval only
            [sys.executable, "-c", script, str(tmp_path)],
            input=json.dumps(event).encode(),
            capture_output=True,
            timeout=30,
            check=False,
            env=environment,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(4)))
    for result in results:
        assert result.returncode == 0, result.stderr
        assert "记忆 😀" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    logs = list((tmp_path / "log/hooks/retrieve").iterdir())
    assert len(logs) == 4 and all(p.suffix == ".json" for p in logs)
    traces = [json.loads(p.read_text(encoding="utf-8")) for p in logs]
    assert {trace["session_id"] for trace in traces} == {"0", "1", "2", "3"}
    assert {trace["query"] for trace in traces} == {f"查询 {index}" for index in range(4)}
    assert all(trace["status"] == "context_returned" for trace in traces)
