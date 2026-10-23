import argparse
import asyncio
import io
import json
import sys

from memu.hosts.codex import memorize_hook


def test_submit_starts_background_without_waiting(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.delenv(memorize_hook.BACKGROUND_ENV, raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit"})))
    monkeypatch.setattr(memorize_hook.notify_console, "launch_background", lambda *args: calls.append(args))
    args = argparse.Namespace(base_dir=str(tmp_path), agent="codex.exe", session_dir="sessions")
    assert asyncio.run(memorize_hook._cmd_memorize_hook(args)) == 0
    argv, layout, _ = calls[0]
    assert argv == ["hook-run", "--base-dir", str(tmp_path), "--agent", "codex.exe", "--session-dir", "sessions"]
    assert layout.base == tmp_path
    assert json.loads(capsys.readouterr().out) == {}


def test_submit_skips_own_background_and_releases_failed_launch(tmp_path, monkeypatch, capsys):
    def fail(*args):
        raise OSError("launch failed")  # noqa: TRY003

    monkeypatch.setattr(memorize_hook.notify_console, "launch_background", fail)
    args = argparse.Namespace(base_dir=str(tmp_path), agent="codex.exe", session_dir="sessions")
    for own in (True, False):
        monkeypatch.setenv(memorize_hook.BACKGROUND_ENV, "1" if own else "")
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit"})))
        assert asyncio.run(memorize_hook._cmd_memorize_hook(args)) == 0
        output = capsys.readouterr()
        assert json.loads(output.out) == {}
        assert ("launch failed" in output.err) is not own


def test_evolve_child_inherits_recursion_guard(tmp_path, monkeypatch, capsys):
    from memu.hosts.bridging import Layout

    monkeypatch.delenv(memorize_hook.BACKGROUND_ENV, raising=False)
    layout = Layout.default("codex", tmp_path)
    script = "import os; print('MEMU_GUARD=' + os.environ.get('MEMU_CODEX_MEMORIZE', 'missing'))"
    memorize_hook.notify_console.stream_agent([sys.executable, "-c", script], layout, "probe", 10)
    assert "MEMU_GUARD=1" in capsys.readouterr().out


def test_invalid_submit_does_not_start_worker(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"Stop"}'))
    assert asyncio.run(memorize_hook._cmd_memorize_hook(argparse.Namespace())) == 0
    result = capsys.readouterr()
    assert json.loads(result.out) == {}
    assert "expected a UserPromptSubmit" in result.err


def test_codex_exposes_submit_entry_and_background_worker():
    from memu.hosts.codex.cli import SPEC
    from memu.hosts.host_cli import build_parser

    parser = build_parser(SPEC)
    assert parser.parse_args(["memorize-hook", "--agent", "codex"]).agent == "codex"
    assert parser.parse_args(["hook-run"]).console is False
    help_text = parser.format_help()
    assert "install-hook" not in help_text
    assert "remove-hook" not in help_text
