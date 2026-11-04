"""Claude request verification mocks the process; no provider requests in CI."""

import json
import subprocess
from pathlib import Path

import pytest

from memu.hosts.claude_code import cli_prepare


def test_standalone_environment_preserves_user_credentials_and_parent(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    retained = {
        "ANTHROPIC_API_KEY": "user-key",
        "ANTHROPIC_AUTH_TOKEN": "user-token",
        "ANTHROPIC_BASE_URL": "https://provider.example",
        "ANTHROPIC_MODEL": "user-model",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "user-opus",
        "CLAUDE_CODE_OAUTH_TOKEN": "user-oauth",
        "HTTPS_PROXY": "https://proxy.example",
    }
    removed = {
        "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1",
        "CLAUDE_CODE_HOST_AUTH_ENV_VAR": "desktop-auth",
        "CLAUDE_CODE_HOST_CREDS_FILE": "desktop-credentials",
        "CLAUDE_CODE_HOST_SESSION_ID": "desktop-session",
        "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH": "1",
        "CLAUDE_CODE_CHILD_SESSION": "1",
        "CLAUDE_CODE_SESSION_ID": "foreground",
        "CLAUDECODE": "frontend",
    }
    for key, value in {**retained, **removed}.items():
        monkeypatch.setenv(key, value)
    env = cli_prepare.standalone_env()
    assert env["CLAUDE_CONFIG_DIR"] == str(tmp_path / ".claude")
    assert all(env[key] == value for key, value in retained.items())
    assert all(key not in env for key in removed)
    assert all(cli_prepare.os.environ[key] == value for key, value in removed.items())


@pytest.mark.parametrize("entrypoint", ["claude-desktop", "claude-desktop-3p"])
def test_desktop_routing_does_not_override_saved_provider(tmp_path, monkeypatch, entrypoint):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    settings = tmp_path / ".claude/settings.json"
    settings.parent.mkdir()
    original = json.dumps({
        "env": {"ANTHROPIC_BASE_URL": "https://provider.example", "ANTHROPIC_AUTH_TOKEN": "saved-token"}
    })
    settings.write_text(original)
    desktop = {
        "CLAUDE_CODE_ENTRYPOINT": entrypoint,
        "CLAUDE_CODE_EXECPATH": "desktop/claude.exe",
        "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH": "1",
        "CLAUDE_CODE_OAUTH_SCOPES": "",
        "CLAUDE_CODE_ATTRIBUTION_HEADER": "desktop",
        "CLAUDE_CODE_DIAGNOSTICS_FILE": "desktop.log",
        "CLAUDE_PID": "123",
        "ANTHROPIC_BASE_URL": "http://localhost:1234/claude-desktop",
        "ANTHROPIC_MODEL": "desktop-model",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "desktop-opus",
    }
    for key, value in desktop.items():
        monkeypatch.setenv(key, value)
    env = cli_prepare.standalone_env()
    assert all(key not in env for key in desktop)
    assert env["CLAUDE_CONFIG_DIR"] == str(settings.parent)
    assert settings.read_text() == original
    assert all(cli_prepare.os.environ[key] == value for key, value in desktop.items())


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
    assert "Reply OK." in output
    assert "Waiting for response" in output
    assert "exit 1" in str(exc.value)
    monkeypatch.setattr(
        cli_prepare.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, json.dumps({"result": "OK saved-secret"}), ""),
    )
    cli_prepare.verify_request(tmp_path / "claude.exe")
    output = capsys.readouterr().out
    assert "← OK [redacted]" in output


@pytest.mark.parametrize("response", ["success", "error", "empty", "invalid", "exit", "timeout"])
def test_minimal_request_is_isolated_and_validates_response(tmp_path, monkeypatch, response):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CLAUDECODE", "frontend")
    monkeypatch.setenv("CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "1")
    monkeypatch.setenv("CLAUDE_CODE_HOST_AUTH_ENV_VAR", "desktop-auth")
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
        assert "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST" not in kwargs["env"]
        assert "CLAUDE_CODE_HOST_AUTH_ENV_VAR" not in kwargs["env"]
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
