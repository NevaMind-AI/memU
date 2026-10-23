from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from memu.hosts.codex import prompt_hook
from memu.hosts.codex.cli import main


@pytest.mark.parametrize("outcome", ["success", "empty", "failure", "timeout", "invalid"])
def test_prompt_hook_preserves_query_and_logs(tmp_path, monkeypatch, capsys, outcome):
    prompt = '  中文 "quoted"\nsecond line  '
    event = {"hook_event_name": "UserPromptSubmit", "session_id": "test-session", "prompt": prompt}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    calls = []

    def retrieve(argv, **kwargs):
        calls.append((argv, kwargs))
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(argv, 45)
        if outcome == "failure":
            return subprocess.CompletedProcess(argv, 1, "", "permission denied")
        if outcome == "invalid":
            return subprocess.CompletedProcess(argv, 0, "[]", "")
        memories = {"segments": [{"content": "记忆"}] if outcome == "success" else [], "files": [], "resources": []}
        return subprocess.CompletedProcess(argv, 0, json.dumps(memories), "")

    monkeypatch.setattr(prompt_hook.subprocess, "run", retrieve)
    assert main(["prompt-hook"]) == 0
    output = capsys.readouterr()
    logs = list((tmp_path / ".memu/hosts/codex/log/hooks/retrieve").glob("*.log"))
    assert not (tmp_path / ".memu/hosts/codex/log/hooks/memorize").exists()
    assert len(logs) == 1
    records = [json.loads(line) for line in logs[0].read_text(encoding="utf-8").splitlines()]
    assert records[0]["status"] == "started"
    final = records[-1]
    assert final["session_id"] == "test-session"
    assert final["elapsed_ms"] >= final["retrieve_elapsed_ms"] >= 0
    assert "second line" not in logs[0].read_text(encoding="utf-8")
    assert calls[0][0] == [sys.executable, "-m", "memu.hosts.codex.cli", "retrieve", prompt]
    assert not calls[0][1].get("shell", False)
    if outcome == "success":
        specific = json.loads(output.out)["hookSpecificOutput"]
        assert specific["hookEventName"] == "UserPromptSubmit"
        assert "记忆" in specific["additionalContext"]
        assert final["additional_context"] == specific["additionalContext"]
        assert f"memU retrieval subprocess elapsed: {final['retrieve_elapsed_ms']} ms" in specific["additionalContext"]
        assert "not total answer time" in specific["additionalContext"]
        assert final["retrieve_result"] == json.loads(specific["additionalContext"].split("\n", 2)[2])
        assert final["status"] == "context_returned"
        assert final["counts"] == {"segments": 1, "files": 0, "resources": 0}
    else:
        assert not output.out
        if outcome != "empty":
            assert final["status"] == "failed"
            assert output.err
    if outcome == "empty":
        assert final["retrieve_result"] == {"segments": [], "files": [], "resources": []}
        assert "additional_context" not in final
    if outcome == "failure":
        assert final["retrieve_exit_code"] == 1
        assert final["stderr"] == "permission denied"


@pytest.mark.parametrize("prompt", ["", []])
def test_prompt_hook_empty_and_invalid_input(tmp_path, monkeypatch, capsys, prompt):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}))
    )
    calls = []
    monkeypatch.setattr(prompt_hook.subprocess, "run", lambda *a, **kw: calls.append(a))
    assert main(["prompt-hook"]) == 0
    assert not calls
    assert not capsys.readouterr().out
    log = next((tmp_path / ".memu/hosts/codex/log/hooks/retrieve").glob("*.log"))
    final = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert final["status"] == ("empty_prompt" if prompt == "" else "failed")
