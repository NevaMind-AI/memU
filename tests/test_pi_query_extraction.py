"""pi extraction isolation, output validation, and hook routing."""

import argparse
import io
import json
from typing import Any

import pytest

from memu.hosts import query_extraction
from memu.hosts.pi import prompt_hook
from memu.hosts.pi import query_extraction as pi


@pytest.mark.parametrize("result", [{"query": "topic"}, {"query": ""}, {"query": "x" * 201}, "not JSON"])
def test_pi_request_and_validation(result, monkeypatch):
    monkeypatch.setattr(pi.shutil, "which", lambda _: "pi.cmd")
    monkeypatch.setenv("USER_PROVIDER", "preserved")

    def run(argv, source, cwd, flags, **kwargs):
        assert argv[0] == "pi.cmd"
        assert all(
            flag in argv
            for flag in (
                "--no-tools",
                "--no-session",
                "--no-extensions",
                "--no-skills",
                "--no-context-files",
                "--offline",
            )
        )
        assert source.decode("utf-8") == query_extraction.extraction_instruction("x" * 600)
        assert argv[argv.index("--provider") + 1] == "provider"
        assert argv[argv.index("--model") + 1] == "model"
        assert cwd.is_dir()
        assert kwargs["env"]["MEMU_BRIDGING_RUN"] == "1"
        assert kwargs["env"]["USER_PROVIDER"] == "preserved"
        return (result if isinstance(result, str) else json.dumps(result)).encode()

    monkeypatch.setattr(query_extraction, "run_extraction", run)
    trace: dict[str, Any] = {}
    selected = pi.select_query("x" * 600, trace, provider="provider", model="model")
    assert selected == ("topic" if result == {"query": "topic"} else "x" * 600)


@pytest.mark.asyncio
async def test_hook_routes_extracted_query(tmp_path, monkeypatch, capsys):
    def extract(prompt, **kwargs):
        assert kwargs == {"provider": "provider", "model": "model"}
        return "topic"

    async def retrieve(query, *, query_kind):
        assert (query, query_kind) == ("topic", "extracted")
        return {"hits": [], "resources": []}

    monkeypatch.setattr(pi, "_extract", extract)
    monkeypatch.setattr(prompt_hook, "retrieve", retrieve)
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"prompt": "x" * 600, "provider": "provider", "model": "model"}))
    )
    assert await prompt_hook.prompt_hook(argparse.Namespace(base_dir=str(tmp_path))) == 0
    capsys.readouterr()
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["query_source"] == "extracted"
    assert trace["query_truncated"] is False
