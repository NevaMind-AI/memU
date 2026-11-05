"""Claude's context ceiling applies to whole JSON entries, including resources."""

from __future__ import annotations

import io
import json
import subprocess
import sys

import pytest

from memu.hosts.claude_code import prompt_hook as hook
from memu.hosts.claude_code.cli import main
from memu.hosts.retrieval import render_context


def test_exact_boundary_keeps_complete_entry() -> None:
    empty = render_context(
        {"hits": [{"text": ""}], "resources": []},
        original={"hits": [{"text": ""}, {"text": "extra"}], "resources": []},
    )
    exact = {"text": "a" * (hook.CONTEXT_BUDGET - len(empty))}
    trace: dict = {}
    context = hook.bounded_context({"hits": [exact, {"text": "extra"}], "resources": []}, trace)
    assert context is not None
    assert trace["context_utf16_units"] == hook.CONTEXT_BUDGET
    result = json.loads(context[len(hook.CONTEXT_PREFIX) :])
    assert result["hits"] == [exact]
    assert result["resources"] == []
    assert result["context_counts"] == {"returned": {"hits": 1, "resources": 0}, "omitted": {"hits": 1, "resources": 0}}
    assert trace["omitted_counts"] == {"hits": 1, "resources": 0}


def test_status_is_preserved_within_the_whole_context_budget() -> None:
    status = {
        "status": "succeeded",
        "query_kind": "short",
        "min_score": 0.55,
        "candidate_segments": 5,
        "filtered_segments": 4,
        "retained_segments": 1,
        "returned_hits": 1,
    }
    payload = {"hits": [{"text": "😀" * 6000}], "resources": [], "retrieval_status": status}
    trace: dict = {}
    context = hook.bounded_context(payload, trace)
    assert context == render_context({"hits": [], "resources": [], "retrieval_status": status}, original=payload)
    result = json.loads(context[len(hook.CONTEXT_PREFIX) :])
    assert result["retrieval_status"]["returned_hits"] == 1
    assert result["context_counts"] == {"returned": {"hits": 0, "resources": 0}, "omitted": {"hits": 1, "resources": 0}}
    assert trace["omitted_counts"] == {"hits": 1, "resources": 0}
    assert trace["context_utf16_units"] <= hook.CONTEXT_BUDGET


def test_oversized_entries_do_not_block_later_hits_or_resources() -> None:
    small = {"text": '中文😀"\\\n', "path": "memory/example.md"}
    resource = {"path": "notes.md", "caption": "complete resource"}
    trace: dict = {}
    context = hook.bounded_context(
        {"hits": [{"text": "😀" * 6000}, small], "resources": [{"caption": "x" * 10000}, resource]}, trace
    )
    assert context is not None
    result = json.loads(context[len(hook.CONTEXT_PREFIX) :])
    assert result["hits"] == [small]
    assert result["resources"] == [resource]
    assert result["context_counts"] == {"returned": {"hits": 1, "resources": 1}, "omitted": {"hits": 1, "resources": 1}}
    assert trace["context_utf16_units"] <= hook.CONTEXT_BUDGET
    assert trace["context_utf16_units"] > trace["context_chars"]
    assert trace["returned_counts"] == {"hits": 1, "resources": 1}
    assert trace["omitted_counts"] == {"hits": 1, "resources": 1}


@pytest.mark.parametrize("payload", [{"hits": [{"text": "x" * 10000}]}, {"retrieval_status": {"detail": "x" * 10000}}])
def test_no_fitting_entries_return_no_context(payload: dict) -> None:
    assert hook.bounded_context(payload, {}) is None


@pytest.mark.parametrize("rewake", [False, True])
@pytest.mark.parametrize(
    "outcome", ["success", "empty", "filtered", "oversized", "failure", "timeout", "invalid", "bad_entry"]
)
def test_cli_returns_context_or_fails_open(tmp_path, monkeypatch, capsys, outcome, rewake):
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
            "filtered": {
                "hits": [],
                "resources": [],
                "retrieval_status": {
                    "status": "succeeded",
                    "query_kind": "short",
                    "min_score": 0.55,
                    "candidate_segments": 5,
                    "filtered_segments": 5,
                    "retained_segments": 0,
                    "returned_hits": 0,
                },
            },
            "oversized": {"hits": [{"text": "x" * 10000}], "resources": []},
            "invalid": [],
            "bad_entry": {"hits": ["not an object"]},
        }[outcome]
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    monkeypatch.setattr(hook.subprocess, "run", retrieve)

    def select(prompt, trace):
        trace.update(query_source="prefix", extraction_status="timeout")
        return prompt[:2000]

    monkeypatch.setattr(hook, "select_query", select)
    options = ["--rewake"] if rewake else []
    has_context = outcome in ("success", "empty", "filtered")
    assert main(["prompt-hook", "--base-dir", str(tmp_path), *options]) == (2 if rewake and has_context else 0)
    output = capsys.readouterr()
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    argv, kwargs = calls[0]
    assert argv == [
        sys.executable,
        "-m",
        "memu.hosts.claude_code.cli",
        "retrieve",
        "--query-stdin",
        "--query-kind",
        "long",
    ]
    assert kwargs["input"].decode("utf-8") == prompt[:2000]
    assert kwargs["env"]["CLAUDE_CODE_SESSION_ID"] == "synthetic-session"
    assert 0 < kwargs["timeout"] <= 40
    assert trace["query_truncated"]
    if has_context:
        context = output.err.strip() if rewake else json.loads(output.out)["hookSpecificOutput"]["additionalContext"]
        if rewake:
            assert not output.out
        assert context.startswith(hook.CONTEXT_PREFIX)
        assert trace["additional_context"] == context
        assert trace["retrieve_result"]["hits"] == ([{"text": "记忆😀"}] if outcome == "success" else [])
        result = json.loads(context[len(hook.CONTEXT_PREFIX) :])
        if outcome == "success":
            assert "记忆😀" in context
        else:
            assert result["hits"] == result["resources"] == []
        if outcome == "filtered":
            assert result["retrieval_status"]["filtered_segments"] == 5
        assert len(context.encode("utf-16-le")) // 2 <= hook.CONTEXT_BUDGET
        assert trace["status"] == ("context_returned" if outcome == "success" else "empty_result")
        assert trace["omitted_counts"] == {"hits": 0, "resources": 0}
    else:
        assert not output.out
        expected = {"empty": "empty_result", "oversized": "budget_exhausted"}.get(outcome, "failed")
        assert trace["status"] == expected
        if outcome == "oversized":
            assert trace["retrieve_result"]["hits"] == [{"text": "x" * 10000}]
            assert trace["additional_context"] is None


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
