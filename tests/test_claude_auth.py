"""Authentication choices mock Claude and never log in or call providers."""

import json
import subprocess
from pathlib import Path

import pytest

from memu.hosts.claude_code import auth, cli_prepare
from memu.hosts.claude_code.cli import main


@pytest.fixture
def machine(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(cli_prepare, "prepare", lambda *a, **k: tmp_path / "claude.exe")
    monkeypatch.setattr(cli_prepare, "auth_status", lambda _: False)
    return tmp_path / ".claude/settings.json"


def test_noninteractive_lists_choices_without_prompting_or_login(machine, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("must not prompt"))
    monkeypatch.setattr(auth.subprocess, "run", lambda *a, **k: pytest.fail("must not log in"))
    assert main(["auth", "--non-interactive", "--method", "login"]) == 2
    assert "cc-switch" in capsys.readouterr().out
    assert not machine.exists()


def test_existing_auth_skips_selection(machine, monkeypatch):
    monkeypatch.setattr(cli_prepare, "auth_status", lambda _: True)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("must not prompt"))
    assert main(["auth"]) == 0


@pytest.mark.parametrize("selection", ["4", "invalid"])
def test_later_or_invalid_does_not_change_settings(machine, monkeypatch, selection):
    monkeypatch.setattr("builtins.input", lambda _: selection)
    assert main(["auth"]) == 2
    assert not machine.exists()


@pytest.mark.parametrize("success", [False, True])
def test_login_uses_default_home_and_rechecks(machine, monkeypatch, success):
    states = iter([False, success])
    monkeypatch.setattr(cli_prepare, "auth_status", lambda _: next(states))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "elsewhere")
    monkeypatch.setenv("CLAUDECODE", "frontend")
    monkeypatch.setenv("CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "1")
    monkeypatch.setenv("CLAUDE_CODE_HOST_AUTH_ENV_VAR", "desktop-auth")

    def login(argv, **kwargs):
        assert argv[1:] == ["auth", "login"]
        assert kwargs["env"]["CLAUDE_CONFIG_DIR"] == str(machine.parent)
        assert "CLAUDECODE" not in kwargs["env"]
        assert "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST" not in kwargs["env"]
        assert "CLAUDE_CODE_HOST_AUTH_ENV_VAR" not in kwargs["env"]
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(auth.subprocess, "run", login)
    assert main(["auth", "--method", "login"]) == (0 if success else 2)


def test_failed_login_stops_before_auth_recheck(machine, monkeypatch):
    monkeypatch.setattr(auth.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 1))
    assert main(["auth", "--method", "login"]) == 2
    assert not machine.exists()


def test_auth_probe_failure_does_not_print_provider_details(machine, monkeypatch, capsys):
    def failed(executable):
        raise ValueError("private-provider-secret")

    monkeypatch.setattr(cli_prepare, "auth_status", failed)
    assert main(["auth", "--non-interactive"]) == 1
    output = capsys.readouterr()
    assert "private-provider-secret" not in output.out + output.err


def test_existing_credentials_are_not_overwritten(machine, monkeypatch):
    machine.parent.mkdir()
    machine.write_text(json.dumps({"env": {"ANTHROPIC_AUTH_TOKEN": "existing-secret"}}))
    original = machine.read_bytes()
    answers = iter(["https://provider.example", "api-key"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(auth.getpass, "getpass", lambda _: "replacement-secret")
    assert main(["auth", "--method", "provider"]) == 2
    assert machine.read_bytes() == original


def test_input_end_returns_blocked_without_changes(machine, monkeypatch, capsys):
    def ended(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", ended)
    assert main(["auth"]) == 2
    assert "Input ended" in capsys.readouterr().out
    assert not machine.exists()


def test_chinese_menu_is_scoped_to_invocation(machine, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "4")
    assert main(["auth", "--language", "zh"]) == 2
    assert "   1. Claude 账号登录" in capsys.readouterr().out
    assert main(["auth"]) == 2
    assert "Claude account login" in capsys.readouterr().out


@pytest.mark.parametrize("kind", ["api-key", "token"])
def test_provider_preserves_settings_and_hides_secret(machine, monkeypatch, capsys, kind):
    machine.parent.mkdir()
    original = {"permissions": {"allow": ["Read"]}, "env": {"KEPT": "yes"}}
    machine.write_text(json.dumps(original))
    states = iter([False, True])
    monkeypatch.setattr(cli_prepare, "auth_status", lambda _: next(states))
    answers = iter(["https://provider.example/v1", kind])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(auth.getpass, "getpass", lambda _: "fixture-secret")
    assert main(["auth", "--method", "provider"]) == 0
    output = capsys.readouterr()
    assert "fixture-secret" not in output.out + output.err
    settings = json.loads(machine.read_text())
    assert settings["permissions"] == original["permissions"]
    assert settings["env"]["KEPT"] == "yes"
    assert settings["env"]["ANTHROPIC_API_KEY" if kind == "api-key" else "ANTHROPIC_AUTH_TOKEN"] == "fixture-secret"


@pytest.mark.parametrize("configured", [False, True])
def test_external_configuration_is_rechecked_without_writing(machine, monkeypatch, configured):
    states = iter([False, configured])
    monkeypatch.setattr(cli_prepare, "auth_status", lambda _: next(states))
    answers = iter(["3", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(auth.getpass, "getpass", lambda _: pytest.fail("external setup must not request credentials"))
    monkeypatch.setattr(
        auth.subprocess, "run", lambda *a, **k: pytest.fail("external setup must not launch login or tools")
    )
    assert main(["auth"]) == (0 if configured else 2)
    assert not machine.exists()


@pytest.mark.parametrize(
    "endpoint", ["", "not-a-url", "https://user:secret@provider.example", "https://provider.example/?token=secret"]
)
def test_bad_endpoint_never_writes_credentials(machine, monkeypatch, endpoint):
    monkeypatch.setattr("builtins.input", lambda _: endpoint)
    monkeypatch.setattr(auth.getpass, "getpass", lambda _: pytest.fail("must validate endpoint first"))
    assert main(["auth", "--method", "provider"]) == 2
    assert not machine.exists()
