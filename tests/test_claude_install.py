"""Claude lifecycle operations preserve user settings and processing state."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from memu.hosts import installation as lifecycle
from memu.hosts.claude_code import auth, cli_prepare, doctor, hook_install, install, memorize_hook
from memu.hosts.claude_code.cli import SPEC, main
from memu.hosts.hooks.admission import workspace_lock

BACKEND = lifecycle.backend


@pytest.fixture
def machine(tmp_path, monkeypatch):
    home = tmp_path / ".claude"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    redirected = tmp_path / "redirected-claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(redirected))
    assert hook_install.home() == home
    executable = tmp_path / "memu-claude-code.exe"
    executable.touch()
    monkeypatch.setattr(sys, "argv", [str(executable)])
    monkeypatch.setattr(install.cli_install, "configure_windows_path", lambda _: None)
    monkeypatch.setattr(cli_prepare, "prepare", lambda *a, **k: tmp_path / "claude.exe")
    monkeypatch.setattr(cli_prepare, "auth_status", lambda _: True)
    calls = []

    async def command(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(install, "_command", command)

    async def backend(args, invoke):
        assert invoke is command
        calls.append(["backend"])

    monkeypatch.setattr(lifecycle, "backend", backend)
    return home, tmp_path / "state", calls


def invoke(machine, *options):
    return main(["install", "--non-interactive", "--json", "--base-dir", str(machine[1]), *options])


@pytest.mark.parametrize("choice", ["login", "provider", "external", "later"])
def test_install_authentication_choices(machine, monkeypatch, capsys, choice):
    calls = []

    def configure(executable, *, method, non_interactive):
        calls.append((method, non_interactive))
        if method == "later":
            raise lifecycle.Blocked("Authentication deferred")  # noqa: TRY003

    monkeypatch.setattr(auth, "configure", configure)
    code = main([
        "install",
        "--skip-cli-test",
        "--json",
        "--language",
        "en",
        "--base-dir",
        str(machine[1]),
        "--auth",
        choice,
    ])
    assert code == (2 if choice == "later" else 0)
    assert calls == [(choice, False)]
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert progress[-1]["complete"] is (choice != "later")
    if choice == "later":
        assert not (machine[0] / "settings.json").exists()


def test_missing_path_reports_selected_executable_before_request(machine, monkeypatch, capsys):
    monkeypatch.setattr(install.shutil, "which", lambda _: None)
    monkeypatch.setattr(cli_prepare, "verify_request", lambda executable: print("REQUEST_STARTED"))
    assert invoke(machine, "--test-cli") == 0
    output = capsys.readouterr()
    assert "Claude CLI:" in output.err
    if sys.platform == "win32":
        assert "PATH: configured; available in new terminals." in output.err
    assert output.err.index("Claude CLI:") < output.err.index("REQUEST_STARTED")


@pytest.mark.parametrize("choice", ["skip", "success", "failure"])
def test_real_request_is_opt_in_for_noninteractive_install(machine, monkeypatch, capsys, choice):
    calls = []

    def verify(executable):
        calls.append(executable)
        if choice == "failure":
            raise ValueError("private-provider-secret")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-provider-secret")
    monkeypatch.setattr(cli_prepare, "verify_request", verify)
    code = invoke(machine, *([] if choice == "skip" else ["--test-cli"]))
    assert code == (1 if choice == "failure" else 0)
    output = capsys.readouterr()
    assert "private-provider-secret" not in output.out + output.err
    progress = [json.loads(line) for line in output.out.splitlines()]
    if choice != "failure":
        assert progress[-1]["cli_request_verified"] is (choice == "success")
    else:
        assert not (machine[0] / "settings.json").exists()
    assert len(calls) == (0 if choice == "skip" else 1)


@pytest.mark.parametrize("answer", ["", "n"])
def test_interactive_request_choice(machine, monkeypatch, capsys, answer):
    calls = []
    monkeypatch.setattr("builtins.input", lambda _: answer)
    monkeypatch.setattr(cli_prepare, "verify_request", lambda executable: calls.append(executable))
    assert main(["install", "--json", "--language", "en", "--base-dir", str(machine[1])]) == 0
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert progress[-1]["cli_request_verified"] is (answer == "")
    assert bool(calls) is (answer == "")


def test_install_uninstall_preserves_third_party_settings_and_processing(machine, capsys):
    home, base, calls = machine
    path = home / "settings.json"
    foreign = {"type": "command", "command": "other-tool", "async": True}
    original: dict[str, Any] = {
        "permissions": {"allow": ["Read"]},
        "env": {"KEPT": "yes"},
        "hooks": {"UserPromptSubmit": [{"matcher": "custom", "hooks": [foreign]}]},
    }
    path.write_text(json.dumps(original), encoding="utf-8")
    base.mkdir()
    state = base / "cursor.json"
    state.write_text("preserved")
    assert invoke(machine) == 0
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert progress[-1]["complete"] is True
    assert progress[-1]["hook_verification"] == "local_settings_readback"
    assert len([row for row in progress if row["status"] == "passed"]) == 5
    installed = json.loads(path.read_text(encoding="utf-8"))
    assert installed["env"] == original["env"]
    assert installed["permissions"] == original["permissions"]
    assert installed["hooks"]["UserPromptSubmit"][0] == original["hooks"]["UserPromptSubmit"][0]
    assert hook_install.problems() == []
    before = path.read_bytes()
    assert invoke(machine) == 0
    assert path.read_bytes() == before
    capsys.readouterr()
    assert main(["uninstall", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["removed"] == 2
    assert json.loads(path.read_text(encoding="utf-8")) == original
    assert state.read_text() == "preserved"
    assert main(["uninstall", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["removed"] == 0
    assert (home / "settings.json.memu-backup").exists()
    assert calls[0] == ["backend"]
    assert not (home.parent / "redirected-claude").exists()


@pytest.mark.parametrize("condition", ["auth", "missing-cli", "disabled", "invalid", "edited-skill"])
def test_install_stops_on_blockers_without_mutating_hooks(machine, monkeypatch, capsys, condition):
    home, _, _ = machine
    path = home / "settings.json"
    path.write_text(
        "{broken" if condition == "invalid" else json.dumps({"disableAllHooks": condition == "disabled"}),
        encoding="utf-8",
    )
    if condition == "auth":
        monkeypatch.setattr(cli_prepare, "auth_status", lambda _: False)
    if condition == "missing-cli":

        def missing(*args, **kwargs):
            raise FileNotFoundError("Standalone Claude CLI unavailable")  # noqa: TRY003

        monkeypatch.setattr(cli_prepare, "prepare", missing)
    if condition == "edited-skill":
        skill = home / "skills/memu-retrieve/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("user content")
    original = path.read_bytes()
    assert invoke(machine) in (1, 2)
    assert path.read_bytes() == original
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False


@pytest.mark.parametrize("error,code", [(EOFError(), 2), (KeyboardInterrupt(), 130)])
def test_input_end_and_cancellation_are_clean(machine, monkeypatch, capsys, error, code):
    def fail(args):
        raise error

    monkeypatch.setattr(install.lifecycle, "_select_language", fail)
    assert invoke(machine) == code
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False


def test_busy_installer_ends_attempt(machine, capsys):
    lock = machine[1] / ".install"
    lock.mkdir(parents=True)
    with workspace_lock(lock) as acquired:
        assert acquired
        assert invoke(machine) == 2
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "blocked"


def test_settings_concurrent_edit_is_not_overwritten(machine):
    path, original, data = hook_install.read()
    path.write_text('{"user":"concurrent"}')
    with pytest.raises(RuntimeError, match="changed"):
        hook_install._write(path, original, data)
    assert json.loads(path.read_text()) == {"user": "concurrent"}


@pytest.mark.parametrize("problem", ["missing", "duplicate", "old", "missing-entry", "disabled"])
def test_doctor_reports_definition_problems(machine, capsys, problem):
    home, base, _ = machine
    hook_install.install(base)
    path = home / "settings.json"
    data = json.loads(path.read_text())
    groups = data["hooks"]["UserPromptSubmit"]
    if problem == "missing":
        groups.pop()
    elif problem == "duplicate":
        groups.append(groups[0])
    elif problem == "old":
        groups[0]["hooks"][0].pop("asyncRewake")
        groups[0]["hooks"][0]["async"] = True
        groups[0]["hooks"][0]["args"].remove("--rewake")
    elif problem == "missing-entry":
        Path(groups[0]["hooks"][0]["command"]).unlink()
    else:
        data["disableAllHooks"] = True
    path.write_text(json.dumps(data))
    assert doctor.check() == 1
    assert "memu-claude-code install" in capsys.readouterr().out
    if problem == "old":
        hook_install.install(base)
        assert hook_install.problems() == []
        handlers = json.loads(path.read_text())["hooks"]["UserPromptSubmit"]
        retrieval = next(h for g in handlers for h in g["hooks"] if h["args"][0] == "prompt-hook")
        assert retrieval["asyncRewake"] is True
        assert "async" not in retrieval
        assert "--rewake" in retrieval["args"]


def test_missing_runtime_cli_fails_open_without_launch(machine, monkeypatch, capsys):
    def missing():
        raise FileNotFoundError("Standalone Claude CLI unavailable")  # noqa: TRY003

    monkeypatch.setattr(cli_prepare, "find_executable", missing)
    monkeypatch.setattr(memorize_hook, "launch_background", lambda args: pytest.fail("must not launch"))
    monkeypatch.delenv(memorize_hook.BACKGROUND_ENV, raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))
    assert main(["memorize-hook"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {}
    assert "Standalone Claude CLI unavailable" in output.err


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_native_discovery_without_path(tmp_path, monkeypatch, platform):
    monkeypatch.setattr(cli_prepare, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    executable = tmp_path / ".local/bin" / ("claude.exe" if platform == "win32" else "claude")
    executable.parent.mkdir(parents=True)
    executable.touch()
    assert cli_prepare.find_executable() == executable.resolve()


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_official_installer_uses_platform_shell(monkeypatch, platform):
    monkeypatch.setattr(cli_prepare, "sys", SimpleNamespace(platform=platform, stderr=sys.stderr))
    monkeypatch.setattr(cli_prepare.cli_install, "sys", SimpleNamespace(platform=platform, stderr=sys.stderr))
    monkeypatch.setattr(cli_prepare.shutil, "which", lambda value: value)
    seen = []

    def download(request, **kwargs):
        assert request.full_url == "https://claude.ai/install." + ("ps1" if platform == "win32" else "sh")
        return io.BytesIO(b"official script")

    def execute(argv, **kwargs):
        assert Path(argv[-1]).read_bytes() == b"official script"
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["check"] is True
        seen.append(argv)

    monkeypatch.setattr(cli_prepare.cli_install.urllib.request, "urlopen", download)
    monkeypatch.setattr(cli_prepare.subprocess, "run", execute)
    cli_prepare._install()
    assert seen[0][0] == ("powershell.exe" if platform == "win32" else "bash")


@pytest.mark.parametrize(
    "relative",
    [
        "Applications/Claude.app/Contents/Resources/claude",
        "AppData/Local/Claude-3p/claude-code/2.1.234/claude.exe",
        "AppData/Roaming/Claude/claude-code/2.1.308/claude.exe",
        "AppData/Local/Packages/Claude_example/LocalCache/Local/Claude-3p/claude-code/2.1.308/abc123/claude.exe",
        "Library/Application Support/Claude/claude-code/2.1.246/claude.app/Contents/MacOS/claude",
        ".config/Claude/claude-code/2.1.308/abc123/claude",
        "custom-xdg/Claude-3p/claude-code/2.1.308/claude",
        ".claude/remote/ccd-cli/2.1.308",
    ],
)
def test_desktop_path_is_skipped_and_explicit_desktop_rejected(tmp_path, monkeypatch, relative):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    desktop = tmp_path / relative
    standalone = tmp_path / "tools/claude"
    desktop.parent.mkdir(parents=True)
    standalone.parent.mkdir()
    desktop.touch()
    standalone.touch()
    monkeypatch.setattr(cli_prepare.os, "get_exec_path", lambda: [str(desktop.parent), str(standalone.parent)])
    monkeypatch.setattr(
        cli_prepare.shutil, "which", lambda name, path=None: str(desktop if path == str(desktop.parent) else standalone)
    )
    assert cli_prepare.find_executable() == standalone.resolve()
    with pytest.raises(FileNotFoundError, match="standalone"):
        cli_prepare.find_executable(str(desktop))


@pytest.mark.parametrize(
    "path",
    [
        "/home/user/.local/share/claude/versions/2.1.317",
        "/opt/homebrew/Caskroom/claude-code/2.1.317/claude",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js",
        "C:/Users/user/AppData/Local/Microsoft/WinGet/Packages/Anthropic.ClaudeCode_example/claude.exe",
    ],
)
def test_standalone_package_paths_are_not_excluded(path):
    assert not cli_prepare._desktop_binary(Path(path))


@pytest.mark.asyncio
async def test_doctor_checks_integration_even_when_backend_fails(monkeypatch):
    from memu.hosts import host_cli

    async def backend(spec, args):
        return 1

    calls = []

    def local():
        calls.append(True)
        return 0

    monkeypatch.setattr(host_cli, "_cmd_backend_doctor", backend)
    monkeypatch.setattr(doctor, "check", local)
    assert await host_cli._cmd_doctor(SPEC, argparse.Namespace()) == 1
    assert calls == [True]


@pytest.mark.parametrize("allowed", [False, True])
def test_missing_cli_installs_only_with_opt_in(tmp_path, monkeypatch, allowed):
    calls: list[str] = []

    def discover(selected=None):
        if not calls:
            raise FileNotFoundError("missing")
        return tmp_path / "claude.exe"

    monkeypatch.setattr(cli_prepare, "find_executable", discover)
    monkeypatch.setattr(cli_prepare, "_install", lambda: calls.append("install"))
    monkeypatch.setattr(
        cli_prepare.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "2.1.312 (Claude Code)\n", ""),
    )
    if allowed:
        assert cli_prepare.prepare(install_missing=True) == tmp_path / "claude.exe"
        assert calls == ["install"]
    else:
        with pytest.raises(FileNotFoundError):
            cli_prepare.prepare()
        assert calls == []


@pytest.mark.parametrize(
    ("logged_in", "method", "provider"),
    [
        (False, "none", "firstParty"),
        (True, "oauth_token", "firstParty"),
        (True, "api_key", "firstParty"),
        (True, "api_key_helper", "firstParty"),
        (True, "third_party", "bedrock"),
        (True, "third_party", "vertex"),
        (True, "third_party", "foundry"),
    ],
)
def test_auth_status_is_read_only_and_clears_frontend_marker(tmp_path, monkeypatch, logged_in, method, provider):
    monkeypatch.setenv("CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "1")
    monkeypatch.setenv("CLAUDE_CODE_HOST_AUTH_ENV_VAR", "desktop-auth")
    monkeypatch.setenv("CLAUDECODE", "frontend")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "redirected"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    def probe(argv, **kwargs):
        assert argv[1:] == ["auth", "status", "--json"]
        assert "CLAUDECODE" not in kwargs["env"]
        assert "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST" not in kwargs["env"]
        assert "CLAUDE_CODE_HOST_AUTH_ENV_VAR" not in kwargs["env"]
        assert kwargs["env"]["CLAUDE_CONFIG_DIR"] == str(tmp_path / ".claude")
        assert kwargs["stdin"] == subprocess.DEVNULL
        return subprocess.CompletedProcess(
            argv,
            0 if logged_in else 1,
            json.dumps({"loggedIn": logged_in, "authMethod": method, "apiProvider": provider}),
            "",
        )

    monkeypatch.setattr(cli_prepare.subprocess, "run", probe)
    assert cli_prepare.auth_status(tmp_path / "claude.exe") is logged_in


@pytest.mark.parametrize("authentication", [True, False, "error"])
def test_doctor_distinguishes_authentication_from_cli_startup(machine, monkeypatch, capsys, authentication):
    hook_install.install(machine[1])

    def auth_status(executable):
        if authentication == "error":
            raise ValueError("private provider diagnostic")  # noqa: TRY003
        return authentication

    monkeypatch.setattr(cli_prepare, "auth_status", auth_status)
    assert doctor.check() == (0 if authentication is True else 1)
    output = capsys.readouterr().out
    assert "claude-cli ok" in output
    assert "claude-cli failed" not in output
    assert "private provider diagnostic" not in output
    if authentication is True:
        assert "authentication configured" in output
        assert "credentials and provider access unverified" in output
    elif authentication is False:
        assert "authentication missing" in output
        assert "cc-switch" in output
    else:
        assert "authentication check failed" in output


def test_uninstall_keeps_compound_commands_and_unrelated_empty_groups(machine, capsys):
    home, base, _ = machine
    path = home / "settings.json"
    compound = {"type": "command", "command": "memu-claude-code memorize-hook && other-tool"}
    original = {"hooks": {"Stop": [{"hooks": []}], "UserPromptSubmit": [{"hooks": [compound]}]}}
    path.write_text(json.dumps(original))
    hook_install.install(base)
    assert main(["uninstall", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["removed"] == 2
    assert json.loads(path.read_text()) == original


def test_shared_backend_configuration_runs_backend_only_doctor(machine, monkeypatch):
    from memu import config_file

    # Exercise the real shared backend gate; no new config or hook checks before registration.
    config_file.write_values({"MEMU_MEMORY_MODE": "cloud", "MEMU_CLOUD_API_KEY": "fixture-only"})
    monkeypatch.setattr(lifecycle, "backend", BACKEND)
    calls = []

    async def command(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(install, "_command", command)
    assert invoke(machine) == 0
    assert calls[0] == ["doctor", "--backend-only"]
