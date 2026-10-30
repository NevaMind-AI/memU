import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from memu.hosts.codex import prompt_hook
from memu.hosts.codex import query_extraction as extraction
from memu.hosts.codex.cli import main


@pytest.mark.parametrize("length", [199, 200, 201, 2000, 2001, 32000, 32001])
@pytest.mark.parametrize("whitespace", ["", " \t\n\u3000"])
def test_length_routing(length, whitespace, monkeypatch):
    calls = []

    def extract(prompt):
        calls.append(prompt)
        return "actual request near the end"

    monkeypatch.setattr(extraction, "_extract", extract)
    prompt = whitespace + "中" * (length // 2) + whitespace + "中" * (length - length // 2) + whitespace
    trace: dict[str, Any] = {}
    query = extraction.select_query(prompt, trace)
    expected = length >= 200 and len(prompt) <= 32000
    assert calls == ([prompt] if expected else [])
    assert query == ("actual request near the end" if expected else prompt[:2000])
    assert trace["query_source"] == ("extracted" if expected else "original" if len(prompt) <= 2000 else "prefix")
    if len(prompt) > 32000:
        assert trace["extraction_status"] == "input_limit"


@pytest.mark.parametrize(
    "error",
    [
        OSError("missing"),
        ValueError("invalid"),
        subprocess.TimeoutExpired("codex", 12),
        subprocess.CalledProcessError(1, "codex"),
    ],
)
def test_failure_falls_back(error, monkeypatch):
    def fail(prompt):
        raise error

    monkeypatch.setattr(extraction, "_extract", fail)
    trace: dict[str, Any] = {}
    assert extraction.select_query("x" * 2500, trace) == "x" * 2000
    assert trace["query_source"] == "prefix"
    assert trace["extraction_status"] == ("timeout" if isinstance(error, subprocess.TimeoutExpired) else "failed")
    assert trace["extraction_elapsed_ms"] >= 0


@pytest.mark.parametrize(
    "value",
    [
        {"query": "topic"},
        {"query": "中" * 200},
        {"query": " "},
        {"query": "中" * 201},
        [],
        {"query": 3},
        "invalid-json",
        None,
    ],
)
def test_extraction_output_and_command(value, monkeypatch):
    monkeypatch.setattr(extraction.shutil, "which", lambda name: "C:/tools/codex.exe")
    prompt = "background" * 300 + "最后需求:修复 WinError 206"

    def run(argv, source, cwd, flags):
        assert "--ephemeral" in argv
        assert argv[argv.index("--disable") + 1] == "hooks"
        assert "notify=[]" in argv
        assert 'model_reasoning_effort="low"' in argv
        assert json.loads(source.decode().split("User message (JSON string):\n")[1]) == prompt
        assert Path(argv[argv.index("--output-schema") + 1]).is_file()
        assert cwd == Path(argv[argv.index("-o") + 1]).parent
        if value is not None:
            Path(argv[argv.index("-o") + 1]).write_text(
                value if value == "invalid-json" else json.dumps(value),
                encoding="utf-8",
            )

    monkeypatch.setattr(extraction, "_run", run)
    if value in ({"query": "topic"}, {"query": "中" * 200}):
        assert extraction._extract(prompt) == value["query"]
    else:
        with pytest.raises((OSError, ValueError)):
            extraction._extract(prompt)


def test_missing_codex(monkeypatch):
    monkeypatch.setattr(extraction.shutil, "which", lambda name: None)
    trace: dict[str, Any] = {}
    assert extraction.select_query("x" * 600, trace) == "x" * 600
    assert trace["extraction_status"] == "failed"


@pytest.mark.parametrize("candidates", [[], [Path("native/codex.exe")]])
def test_windows_npm_wrapper_resolution(candidates, monkeypatch):
    monkeypatch.setattr(extraction, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(extraction.shutil, "which", lambda name: "C:/tools/codex.CMD")
    monkeypatch.setattr(Path, "glob", lambda *a: iter(candidates))
    monkeypatch.setattr(extraction.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    seen = []

    def run(argv, source, cwd, flags):
        seen.append(argv)
        Path(argv[argv.index("-o") + 1]).write_text('{"query":"topic"}', encoding="utf-8")

    monkeypatch.setattr(extraction, "_run", run)
    trace: dict[str, Any] = {}
    assert extraction.select_query("x" * 600, trace) == ("topic" if candidates else "x" * 600)
    assert bool(seen) is bool(candidates)
    if candidates:
        assert seen[0][0] == str(candidates[0])


def test_real_process_stdin_and_nonzero_exit(tmp_path):
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    output = tmp_path / "stdin.txt"
    extraction._run(
        [
            sys.executable,
            "-c",
            "import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",
            str(output),
        ],
        "中文😀".encode(),
        tmp_path,
        flags,
    )
    assert output.read_bytes() == "中文😀".encode()
    with pytest.raises(subprocess.CalledProcessError):
        extraction._run([sys.executable, "-c", "raise SystemExit(3)"], b"", tmp_path, flags)


def test_real_timeout_reaps_agent_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(extraction, "EXTRACT_TIMEOUT", 2)
    real_popen = subprocess.Popen
    seen = []

    def popen(argv, **kwargs):
        if argv[0] != sys.executable:
            return real_popen(argv, **kwargs)
        assert kwargs["env"]["MEMU_CODEX_MEMORIZE"] == "1"
        assert kwargs["env"]["MEMU_BRIDGING_RUN"] == "1"
        assert kwargs["start_new_session"] is (sys.platform != "win32")
        process = real_popen(argv, **kwargs)
        seen.append(process)
        return process

    monkeypatch.setattr(extraction.subprocess, "Popen", popen)
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    marker = tmp_path / "child.pid"
    script = (
        "import pathlib,subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(60)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        extraction._run([sys.executable, "-c", script, str(marker)], b"", tmp_path, flags)
    assert seen[0].poll() is not None
    child_pid = marker.read_text()
    if sys.platform == "win32":
        result = subprocess.run(  # noqa: S603
            ["tasklist", "/FI", f"PID eq {child_pid}", "/FO", "CSV", "/NH"],  # noqa: S607
            capture_output=True,
            check=True,
            timeout=5,
            creationflags=flags,
        )
        assert f'"{child_pid}"'.encode() not in result.stdout
    else:
        result = subprocess.run(  # noqa: S603
            ["ps", "-o", "stat=", "-p", child_pid],  # noqa: S607
            capture_output=True,
            check=False,
            timeout=5,
        )
        assert not result.stdout.strip() or result.stdout.strip().startswith(b"Z")


def test_hook_retrieves_extracted_query_with_shared_deadline(tmp_path, monkeypatch, capsys):
    prompt = "背景" * 1500 + "实际需求:Windows hook WinError 206"
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}))
    )
    seen = []
    clock = [100.0]

    def extract(text):
        assert text == prompt
        clock[0] += 6
        return "Windows hook WinError 206"

    def retrieve(argv, **kwargs):
        assert argv[-2:] == ["--query-kind", "extracted"]
        seen.append(kwargs)
        clock[0] += 2
        return subprocess.CompletedProcess(argv, 0, b'{"hits":[]}', b"")

    monkeypatch.setattr(extraction, "_extract", extract)
    monkeypatch.setattr(prompt_hook.subprocess, "run", retrieve)
    # Isolate the clock from asyncio and account for extraction without actually waiting.
    timer = SimpleNamespace(monotonic=lambda: clock[0])
    monkeypatch.setattr(prompt_hook, "time", timer)
    monkeypatch.setattr(extraction, "time", timer)
    assert main(["prompt-hook", "--base-dir", str(tmp_path)]) == 0
    assert seen[0]["input"] == b"Windows hook WinError 206"
    assert 0 < seen[0]["timeout"] <= 37
    assert "completed successfully" in capsys.readouterr().out
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.log")).read_text().splitlines()[-1])
    assert trace["query_source"] == "extracted"
    assert trace["query_truncated"] is False
    assert prompt not in json.dumps(trace)
    assert "Windows hook WinError 206" not in json.dumps(trace)
    assert trace["extraction_elapsed_ms"] == 6000
