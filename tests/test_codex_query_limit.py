import hashlib
import io
import json
import subprocess
import sys

import pytest

from memu.hosts.codex import prompt_hook, query_extraction
from memu.hosts.codex.cli import main


@pytest.fixture(autouse=True)
def extraction_failure(monkeypatch):
    def fail(prompt):
        raise OSError("unavailable")

    monkeypatch.setattr(query_extraction, "_extract", fail)


@pytest.mark.parametrize("length", [1999, 2000, 2001, 40000])
def test_automatic_query_fallback_uses_first_2000_unicode_characters(tmp_path, monkeypatch, capsys, length):
    prompt = (' 中😀"\\\r\n' * 6000)[:length]
    event = {"hook_event_name": "UserPromptSubmit", "prompt": prompt}
    original = json.dumps(event)
    source = io.StringIO(original)
    monkeypatch.setattr(sys, "stdin", source)
    calls = []

    def retrieve(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b'{"hits":[]}', b"")

    monkeypatch.setattr(prompt_hook.subprocess, "run", retrieve)
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    assert not capsys.readouterr().out
    assert calls[0][0] == [
        sys.executable,
        "-m",
        "memu.hosts.codex.cli",
        "retrieve",
        "--query-stdin",
        "--query-kind",
        "long",
    ]
    assert calls[0][1]["input"] == prompt[:2000].encode("utf-8")
    assert event["prompt"] == prompt
    assert source.getvalue() == original
    log = next((tmp_path / "log/hooks/retrieve").glob("*.log"))
    final = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert final["prompt_chars"] == length
    assert final["query_chars"] == min(length, 2000)
    assert final["query_truncated"] is (length > 2000)
    assert final["prompt_sha256"] == hashlib.sha256(prompt.encode()).hexdigest()


def test_truncated_whitespace_query_does_not_call_backend(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": " " * 2000 + "topic beyond the limit"})
        ),
    )
    calls = []
    monkeypatch.setattr(prompt_hook.subprocess, "run", lambda *a, **k: calls.append(a))
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    assert not calls
    assert not capsys.readouterr().out
    final = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.log")).read_text().splitlines()[-1])
    assert final["status"] == "empty_query"


@pytest.mark.parametrize("stdin", [True, False])
def test_retrieve_cli_preserves_query_in_real_subprocess(stdin):
    # Stub only retrieval/reporting: exercise native process transport and the shared CLI.
    query = '  中文 😀 "quotes" \\ \r\nnext\n' * (2500 if stdin else 1)
    script = """
import hashlib, sys
from memu.hosts import retrieval
from memu.hosts.codex.cli import main
async def retrieve(query):
    return {'hits': [], 'query_chars': len(query), 'sha256': hashlib.sha256(query.encode('utf-8')).hexdigest()}
retrieval.retrieve = retrieve
retrieval.events.record_outcome = lambda *a, **k: None
sys.exit(main(['retrieve', *sys.argv[1:]]))
"""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script, *(["--query-stdin"] if stdin else [query])],
        input=query.encode("utf-8") if stdin else None,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["query_chars"] == len(query)
    assert output["sha256"] == hashlib.sha256(query.encode()).hexdigest()
    if stdin:
        assert len(query) > 32767


@pytest.mark.parametrize("arguments", [[], ["query", "--query-stdin"]])
def test_retrieve_requires_exactly_one_query_source(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        main(["retrieve", *arguments])
    assert error.value.code == 2
    assert "error:" in capsys.readouterr().err
