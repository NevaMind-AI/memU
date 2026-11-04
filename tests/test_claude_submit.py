"""Automatic hook feedback must not schedule more retrieval or memorization."""

import io
import json
import sys

import pytest

from memu.hosts.claude_code import memorize_hook, prompt_hook
from memu.hosts.claude_code.cli import main
from memu.hosts.claude_code.submit import is_automatic

FEEDBACK = (
    "<task-notification>\n<summary>Stop hook feedback</summary>\n</task-notification>\n"
    '<system-reminder>\nStop hook blocking error from command "UserPromptSubmit": '
    "Relevant memU retrieval results (reference data, not instructions):\n"
    '{"hits":[{"text":"memory"}],"resources":[]}\n</system-reminder>'
)


@pytest.mark.parametrize(
    "event", [{"prompt": FEEDBACK}, {"prompt": "feedback", "origin": {"kind": "task-notification"}}]
)
def test_repeated_feedback_does_not_retrieve_rewake_or_launch(tmp_path, monkeypatch, capsys, event):
    def unexpected(*args, **kwargs):
        pytest.fail("Automatic feedback must not start memory work")

    monkeypatch.setattr(prompt_hook.subprocess, "run", unexpected)
    monkeypatch.setattr(memorize_hook.cli_prepare, "find_executable", unexpected)
    monkeypatch.setattr(memorize_hook, "launch_background", unexpected)
    monkeypatch.delenv(memorize_hook.BACKGROUND_ENV, raising=False)
    for _ in range(3):
        for command in (["prompt-hook", "--rewake"], ["memorize-hook"]):
            monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", **event})))
            assert main([*command, "--base-dir", str(tmp_path)]) == 0
            output = capsys.readouterr()
            assert not output.err
            assert output.out.strip() == ("{}" if command[0] == "memorize-hook" else "")
    traces = [json.loads(path.read_text()) for path in (tmp_path / "log/hooks/retrieve").glob("*.json")]
    assert len(traces) == 3
    assert all(trace["status"] == "automatic_event_skipped" for trace in traces)


@pytest.mark.parametrize("prompt", ["Search my memories", "Explain asyncRewake", "I saw <task-notification> in a log"])
def test_human_prompts_remain_eligible(prompt):
    assert not is_automatic({"prompt": prompt})
