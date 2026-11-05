"""Both adapters follow the same query policy; Claude isolates its request."""

import io
import json
import subprocess
import sys
from typing import Any

import pytest

from memu.hosts import query_extraction
from memu.hosts.claude_code import prompt_hook
from memu.hosts.claude_code import query_extraction as claude
from memu.hosts.codex import query_extraction as codex


@pytest.mark.parametrize("adapter", [codex, claude])
@pytest.mark.parametrize("outcome", ["short", "success", "timeout", "failure", "input_limit"])
def test_shared_selection(adapter, outcome, monkeypatch):
    prompt = "topic" if outcome == "short" else "x" * (32001 if outcome == "input_limit" else 2500)
    calls = []

    def extract(value):
        calls.append(value)
        if outcome == "timeout":
            raise subprocess.TimeoutExpired("agent", 12)
        if outcome == "failure":
            raise ValueError("invalid output")  # noqa: TRY003
        return "extracted topic"

    monkeypatch.setattr(adapter, "_extract", extract)
    trace: dict[str, Any] = {}
    assert adapter.select_query(prompt, trace) == ("extracted topic" if outcome == "success" else prompt[:2000])
    assert bool(calls) == (outcome not in ("short", "input_limit"))
    assert trace["extraction_status"] == {"short": "not_needed", "success": "succeeded", "failure": "failed"}.get(
        outcome, outcome
    )


@pytest.mark.parametrize(
    "value",
    [
        {"result": '{"query":"topic"}'},
        {"result": '{"query":""}'},
        {"result": '{"query":"' + "x" * 201 + '"}'},
        {"result": "not json"},
        {"result": None},
        {"is_error": True, "result": '{"query":"topic"}'},
    ],
)
def test_claude_request_and_validation(value, monkeypatch):
    monkeypatch.setattr(claude.cli_prepare, "find_executable", lambda: "standalone-claude")
    monkeypatch.setattr(claude.cli_prepare, "standalone_env", lambda: {"USER_PROVIDER": "preserved"})

    def run(argv, source, cwd, flags, **kwargs):
        assert argv[0] == "standalone-claude"
        assert argv[argv.index("--tools") + 1] == ""
        assert json.loads(argv[argv.index("--settings") + 1]) == {"disableAllHooks": True}
        assert json.loads(argv[argv.index("--mcp-config") + 1]) == {"mcpServers": {}}
        assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
        assert source.decode() == query_extraction.extraction_instruction("x" * 600)
        assert cwd.is_dir()
        assert kwargs["env"] == {"USER_PROVIDER": "preserved", "MEMU_BRIDGING_RUN": "1", "MEMU_CLAUDE_MEMORIZE": "1"}
        return json.dumps(value).encode()

    monkeypatch.setattr(query_extraction, "run_extraction", run)
    trace: dict[str, Any] = {}
    assert claude.select_query("x" * 600, trace) == ("topic" if value == {"result": '{"query":"topic"}'} else "x" * 600)


def test_claude_hook_uses_extracted_query_and_remaining_deadline(monkeypatch):
    monkeypatch.delenv("MEMU_CLAUDE_MEMORIZE", raising=False)
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "x" * 600}))
    )
    monkeypatch.setattr(claude, "_extract", lambda prompt: "topic")
    ticks = iter([0, 12])
    monkeypatch.setattr(prompt_hook.time, "monotonic", lambda: next(ticks, 12))

    def retrieve(argv, **kwargs):
        assert argv[-2:] == ["--query-kind", "extracted"]
        assert kwargs["input"] == b"topic"
        assert kwargs["timeout"] == 28
        return subprocess.CompletedProcess(argv, 0, b'{"hits":[],"resources":[]}', b"")

    monkeypatch.setattr(prompt_hook.subprocess, "run", retrieve)
    trace: dict[str, Any] = {}
    assert prompt_hook._retrieve(trace) is not None
    assert trace["query_source"] == "extracted"
