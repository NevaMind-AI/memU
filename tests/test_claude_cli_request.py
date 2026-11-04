"""Claude request verification mocks the process; no provider requests in CI."""

import json
import subprocess
from pathlib import Path

import pytest

from memu.hosts.claude_code import cli_prepare


def test_visible_response_and_provider_error_are_redacted(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    directory = tmp_path / ".claude"
    directory.mkdir()
    (directory / "settings.json").write_text(json.dumps({"env": {"ANTHROPIC_AUTH_TOKEN": "saved-secret"}}))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "environment-secret")
    message = (
        "Model demo[1m] unavailable; saved-secret environment-secret https://private.example/path Bearer unknown-secret"
    )
    monkeypatch.setattr(
        cli_prepare.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, json.dumps({"is_error": True, "result": message}), ""),
    )
    with pytest.raises(ValueError, match="Model demo") as exc:
        cli_prepare.verify_request(tmp_path / "claude.exe")
    assert "saved-secret" not in str(exc.value)
    assert "environment-secret" not in str(exc.value)
    assert "private.example" not in str(exc.value)
    assert "unknown-secret" not in str(exc.value)
    output = capsys.readouterr().out
    assert "Request: Reply OK." in output
    assert "Waiting for Claude" in output
    assert "exit 1" in output
    monkeypatch.setattr(
        cli_prepare.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, json.dumps({"result": "OK saved-secret"}), ""),
    )
    cli_prepare.verify_request(tmp_path / "claude.exe")
    output = capsys.readouterr().out
    assert "Response: OK [redacted]" in output


@pytest.mark.parametrize("response", ["success", "error", "empty", "invalid", "exit", "timeout"])
def test_minimal_request_is_isolated_and_validates_response(tmp_path, monkeypatch, response):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CLAUDECODE", "frontend")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "foreground")
    directories = []

    def run(argv, **kwargs):
        assert argv[1:4] == ["-p", "Reply OK.", "--output-format"]
        assert "--no-session-persistence" in argv
        assert argv[argv.index("--tools") + 1] == ""
        assert json.loads(argv[argv.index("--settings") + 1])["disableAllHooks"] is True
        assert json.loads(argv[argv.index("--mcp-config") + 1]) == {"mcpServers": {}}
        assert kwargs["timeout"] == 60
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["env"]["CLAUDE_CONFIG_DIR"] == str(tmp_path / ".claude")
        assert "CLAUDECODE" not in kwargs["env"]
        assert "CLAUDE_CODE_SESSION_ID" not in kwargs["env"]
        directories.append(Path(kwargs["cwd"]))
        assert directories[-1].is_dir()
        if response == "timeout":
            raise subprocess.TimeoutExpired(argv, 60)
        value = {"result": "anything valid", "is_error": response == "error"}
        if response == "empty":
            value["result"] = " "
        return subprocess.CompletedProcess(
            argv,
            1 if response == "exit" else 0,
            "invalid" if response == "invalid" else json.dumps(value),
            "private-error",
        )

    monkeypatch.setattr(cli_prepare.subprocess, "run", run)
    if response == "success":
        cli_prepare.verify_request(tmp_path / "claude.exe")
    else:
        with pytest.raises((ValueError, subprocess.TimeoutExpired)):
            cli_prepare.verify_request(tmp_path / "claude.exe")
    assert not directories[0].exists()
