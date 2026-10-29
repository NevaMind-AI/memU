import io
import json
import sys

import pytest

from memu.hosts.claude_code import prompt_hook
from memu.hosts.claude_code.cli import main


@pytest.mark.parametrize("hits", [[], [{"text": "记忆", "score": 0.7}]])
def test_native_hook_delivers_status_even_when_empty(tmp_path, monkeypatch, capsys, hits):
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "余时遗物架构"}))
    )
    monkeypatch.setattr(prompt_hook.events, "record_outcome", lambda *a, **k: None)

    async def retrieve(query, *, query_kind):
        assert query == "余时遗物架构"
        assert query_kind == "short"
        return {
            "hits": hits,
            "resources": [],
            "retrieval_status": {"status": "succeeded", "candidate_segments": 10, "returned_hits": len(hits)},
        }

    monkeypatch.setattr(prompt_hook, "retrieve", retrieve)
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    context = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    result = json.loads(context.split("\n", 1)[1])
    assert result["hits"] == hits
    assert result["retrieval_status"]["candidate_segments"] == 10
    assert result["context_counts"]["hits"] == len(hits)
    log = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert log["status"] == "context_returned"


def test_context_budget_keeps_filter_status():
    result = {"hits": [{"text": "😀" * 6000}], "resources": [], "retrieval_status": {"filtered_segments": 5}}
    context = prompt_hook._context(result)
    assert len(context.encode("utf-16-le")) // 2 <= 9500
    selected = json.loads(context.split("\n", 1)[1])
    assert selected["hits"] == []
    assert selected["retrieval_status"] == result["retrieval_status"]
    assert selected["context_counts"]["hits"] == 0


@pytest.mark.parametrize("prompt", ["", "topic"])
def test_empty_and_self_run_do_not_retrieve(tmp_path, monkeypatch, capsys, prompt):
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}))
    )
    monkeypatch.setenv("MEMU_CLAUDE_MEMORIZE", "1")
    monkeypatch.setattr(prompt_hook, "retrieve", lambda *a, **k: pytest.fail("unexpected retrieval"))
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    assert not capsys.readouterr().out
