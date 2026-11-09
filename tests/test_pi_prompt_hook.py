from __future__ import annotations

import argparse
import io
import json

import pytest

from memu.hosts import instruction
from memu.hosts.pi import hook_install, prompt_hook, query_extraction


def test_owned_extension_install_and_remove(tmp_path, monkeypatch):
    home = tmp_path / "agent"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(home))
    unrelated = home / "extensions/other.ts"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("// user extension", encoding="utf-8")
    rules = home / "AGENTS.md"
    rules.write_text("# My rules\n", encoding="utf-8")
    instruction.install(rules, "memu-pi", skill=True)
    instruction.install_skill(home / "skills", "memu-pi")
    extra = home / "skills/memu-retrieve/notes.txt"
    extra.write_text("user notes", encoding="utf-8")
    before = {path: path.read_bytes() for path in (rules, instruction.skill_path(home / "skills"), extra)}
    target = hook_install.install(tmp_path / "data")
    assert all(path.read_bytes() == content for path, content in before.items())
    original = target.read_text(encoding="utf-8")
    assert "__MEMU_" not in original
    assert "prompt-hook" in original
    assert hook_install.install(tmp_path / "data").read_text(encoding="utf-8") == original
    assert unrelated.read_text(encoding="utf-8") == "// user extension"
    target.write_text("// user extension", encoding="utf-8")
    with pytest.raises(ValueError, match="unowned"):
        hook_install.install(tmp_path / "data")


@pytest.mark.asyncio
async def test_prompt_hook_returns_context_and_log(tmp_path, monkeypatch, capsys):
    calls = []

    async def retrieve(query, *, query_kind):
        calls.append((query, query_kind))
        return {"hits": [{"text": "An independently meaningful memory"}], "resources": []}

    def failed_extraction(*args, **kwargs):
        raise ValueError("invalid extraction")  # noqa: TRY003

    monkeypatch.setattr(query_extraction, "_extract", failed_extraction)
    monkeypatch.setattr(prompt_hook, "retrieve", retrieve)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "a" * 2100, "session_id": "s"})))
    assert await prompt_hook.prompt_hook(argparse.Namespace(base_dir=str(tmp_path))) == 0
    result = json.loads(capsys.readouterr().out)
    assert "An independently meaningful memory" in result["context"]
    assert calls == [("a" * 2000, "long")]
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["query_truncated"] is True
    assert trace["extraction_status"] == "failed"
    assert trace["session_id"] == "s"
    assert trace["returned_counts"] == {"hits": 1, "resources": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ['{"prompt": 4}', '{"prompt":"hello","source":"extension"}', "null"])
async def test_invalid_or_recursive_input_does_not_retrieve(tmp_path, monkeypatch, capsys, payload):
    async def unexpected(*args, **kwargs):
        pytest.fail("Retrieval must not run")

    monkeypatch.setattr(prompt_hook, "retrieve", unexpected)
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    await prompt_hook.prompt_hook(argparse.Namespace(base_dir=str(tmp_path)))
    assert json.loads(capsys.readouterr().out) == {"context": None}


@pytest.mark.asyncio
async def test_retrieval_failure_is_logged(tmp_path, monkeypatch, capsys):
    async def failure(*args, **kwargs):
        raise TimeoutError("retrieval timed out")  # noqa: TRY003

    monkeypatch.setattr(prompt_hook, "retrieve", failure)
    monkeypatch.setattr("sys.stdin", io.StringIO('{"prompt":"hello"}'))
    await prompt_hook.prompt_hook(argparse.Namespace(base_dir=str(tmp_path)))
    assert json.loads(capsys.readouterr().out) == {"context": None}
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["status"] == "failed"
    assert trace["error_type"] == "TimeoutError"


@pytest.mark.asyncio
async def test_remove_preserves_foreign_extensions(tmp_path, monkeypatch):
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path))
    target = hook_install.install(tmp_path / "data")
    await hook_install._remove(argparse.Namespace())
    assert not target.exists()
    await hook_install._remove(argparse.Namespace())
    target.write_text("// user extension", encoding="utf-8")
    with pytest.raises(ValueError, match="unowned"):
        await hook_install._remove(argparse.Namespace())
