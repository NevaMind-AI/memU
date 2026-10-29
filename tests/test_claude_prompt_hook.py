"""Claude's context ceiling applies to whole JSON entries, including resources."""

from __future__ import annotations

import io
import json
import subprocess
import sys

import pytest

from memu.hosts.claude_code import prompt_hook as hook
from memu.hosts.claude_code.cli import main


def test_exact_boundary_keeps_complete_entry() -> None:
    empty = hook.CONTEXT_PREFIX + json.dumps(
        {"hits": [{"text": ""}], "resources": []}, ensure_ascii=False, separators=(",", ":")
    )
    exact = {"text": "a" * (hook.CONTEXT_BUDGET - len(empty))}
    trace: dict = {}
    context = hook.bounded_context({"hits": [exact, {"text": "extra"}], "resources": []}, trace)
    assert context is not None
    assert trace["context_utf16_units"] == hook.CONTEXT_BUDGET
    assert json.loads(context[len(hook.CONTEXT_PREFIX) :]) == {"hits": [exact], "resources": []}
    assert trace["omitted_counts"] == {"hits": 1, "resources": 0}


def test_oversized_entries_do_not_block_later_hits_or_resources() -> None:
    small = {"text": '中文😀"\\\n', "path": "memory/example.md"}
    resource = {"path": "notes.md", "caption": "complete resource"}
    trace: dict = {}
    context = hook.bounded_context(
        {"hits": [{"text": "😀" * 6000}, small], "resources": [{"caption": "x" * 10000}, resource]}, trace
    )
    assert context is not None
    assert json.loads(context[len(hook.CONTEXT_PREFIX) :]) == {"hits": [small], "resources": [resource]}
    assert trace["context_utf16_units"] <= hook.CONTEXT_BUDGET
    assert trace["context_utf16_units"] > trace["context_chars"]
    assert trace["returned_counts"] == {"hits": 1, "resources": 1}
    assert trace["omitted_counts"] == {"hits": 1, "resources": 1}


@pytest.mark.parametrize("payload", [{"hits": []}, {"hits": [{"text": "x" * 10000}]}])
def test_no_fitting_entries_return_no_context(payload: dict) -> None:
    assert hook.bounded_context(payload, {}) is None


@pytest.mark.parametrize("outcome", ["success", "empty", "oversized", "failure", "timeout", "invalid", "bad_entry"])
def test_cli_returns_context_or_fails_open(tmp_path, monkeypatch, capsys, outcome):
    prompt = '中文😀"\r\n' * 600
    event = {"hook_event_name": "UserPromptSubmit", "session_id": "synthetic-session", "prompt": prompt}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    monkeypatch.delenv("MEMU_CLAUDE_MEMORIZE", raising=False)
    calls = []

    def retrieve(argv, **kwargs):
        calls.append((argv, kwargs))
        if outcome == "failure":
            return subprocess.CompletedProcess(argv, 1, b"", b"backend failed")
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(argv, 40)
        payload = {
            "success": {"hits": [{"text": "记忆😀"}], "resources": []},
            "empty": {"hits": [], "resources": []},
            "oversized": {"hits": [{"text": "x" * 10000}], "resources": []},
            "invalid": [],
            "bad_entry": {"hits": ["not an object"]},
        }[outcome]
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    monkeypatch.setattr(hook.subprocess, "run", retrieve)
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    output = capsys.readouterr()
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    argv, kwargs = calls[0]
    assert argv == [sys.executable, "-m", "memu.hosts.claude_code.cli", "retrieve", "--query-stdin"]
    assert kwargs["input"].decode("utf-8") == prompt[:2000]
    assert kwargs["env"]["CLAUDE_CODE_SESSION_ID"] == "synthetic-session"
    assert kwargs["timeout"] == 40
    assert trace["query_truncated"]
    if outcome == "success":
        context = json.loads(output.out)["hookSpecificOutput"]["additionalContext"]
        assert "记忆😀" in context
        assert len(context.encode("utf-16-le")) // 2 <= hook.CONTEXT_BUDGET
        assert trace["status"] == "context_returned"
        assert trace["omitted_counts"] == {"hits": 0, "resources": 0}
    else:
        assert not output.out
        expected = {"empty": "empty_result", "oversized": "budget_exhausted"}.get(outcome, "failed")
        assert trace["status"] == expected


@pytest.mark.parametrize(
    "payload", ["{broken", "[]", '{"hook_event_name":"Stop"}', '{"hook_event_name":"UserPromptSubmit","prompt":5}']
)
def test_invalid_event_fails_open(tmp_path, monkeypatch, capsys, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    monkeypatch.setattr(hook.subprocess, "run", lambda *a, **k: pytest.fail("must not retrieve"))
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    assert not capsys.readouterr().out


@pytest.mark.parametrize("self_run", [False, True])
def test_blank_query_and_self_run_do_not_retrieve(tmp_path, monkeypatch, capsys, self_run):
    monkeypatch.setenv("MEMU_CLAUDE_MEMORIZE", "1" if self_run else "0")
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "normal" if self_run else " \n"})),
    )
    monkeypatch.setattr(hook.subprocess, "run", lambda *a, **k: pytest.fail("must not retrieve"))
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    assert not capsys.readouterr().out


def test_log_failure_does_not_discard_context(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "_retrieve", lambda trace: {"hookSpecificOutput": {"additionalContext": "memory"}})
    base = tmp_path / "not-a-directory"
    base.write_text("file")
    assert main(["prompt-hook", "--base-dir", str(base)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["hookSpecificOutput"]["additionalContext"] == "memory"
    assert "log failed" in output.err
