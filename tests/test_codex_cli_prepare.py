"""Behavioral cases for the first Codex installation stage."""

import io
import json
import subprocess
import urllib.error
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest

from memu.hosts.codex import cli_prepare as setup
from memu.hosts.codex.cli import main


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(setup.shutil, "which", lambda _: None)
    monkeypatch.setattr(setup, "_installation_directory", lambda: tmp_path)

    def probe(argv, **kwargs):
        assert argv[1:] == ["--version"]
        assert Path(argv[0]).is_absolute()
        assert kwargs["timeout"] == 20
        return subprocess.CompletedProcess(argv, 0, "codex-cli 0.163.0\n", "")

    monkeypatch.setattr(setup.subprocess, "run", probe)
    return tmp_path


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
@pytest.mark.parametrize("source", ["explicit", "path", "installation-directory"])
def test_reuses_executable_without_installing(environment, monkeypatch, platform, source):
    monkeypatch.setattr(setup.sys, "platform", platform)
    binary = environment / ("codex.exe" if platform == "win32" else "codex")
    binary.touch()
    if source == "path":
        monkeypatch.setattr(setup.shutil, "which", lambda _: str(binary))
    monkeypatch.setattr(setup, "_install", lambda: pytest.fail("Existing CLI must not be reinstalled"))
    result = setup.prepare(str(binary) if source == "explicit" else None, install_missing=True)
    assert result["status"] == "passed"
    assert result["executable"] == str(binary.resolve())


def test_invalid_explicit_selection_never_falls_back(environment, monkeypatch):
    (environment / "codex").touch()
    monkeypatch.setattr(setup, "_install", lambda: pytest.fail("Invalid selection must not trigger installation"))
    assert setup.prepare(str(environment / "missing"), install_missing=True)["status"] == "blocked"


def test_missing_noninteractive_does_not_prompt_or_install(environment, monkeypatch, capsys):
    monkeypatch.setattr(setup, "_install", lambda: pytest.fail("Installation requires opt-in"))
    assert main(["prepare-cli", "--json"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "blocked"
    assert result["reason"] == "missing"


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
def test_install_rediscovers_with_stale_path(environment, monkeypatch, platform):
    monkeypatch.setattr(setup.sys, "platform", platform)
    calls = []

    def install():
        calls.append("install")
        (environment / ("codex.exe" if platform == "win32" else "codex")).touch()

    monkeypatch.setattr(setup, "_install", install)
    assert setup.prepare(install_missing=True)["status"] == "passed"
    assert setup.prepare(install_missing=True)["status"] == "passed"
    assert calls == ["install"]


@pytest.mark.parametrize(
    "failure", [subprocess.CalledProcessError(1, "installer"), subprocess.TimeoutExpired("installer", 300)]
)
def test_installer_failure_stops_before_probe(environment, monkeypatch, failure):
    def install():
        raise failure

    monkeypatch.setattr(setup, "_install", install)
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k: pytest.fail("Must not probe after installer failure"))
    assert setup.prepare(install_missing=True)["status"] == "failed"


def test_successful_installer_without_binary_is_blocked(environment, monkeypatch):
    monkeypatch.setattr(setup, "_install", lambda: None)
    assert setup.prepare(install_missing=True)["reason"] == "install_incomplete"


@pytest.mark.parametrize("returncode, stdout", [(1, ""), (0, "unexpected output")])
def test_broken_existing_cli_is_not_reinstalled(environment, monkeypatch, returncode, stdout):
    binary = environment / "selected"
    binary.touch()
    monkeypatch.setattr(setup, "_install", lambda: pytest.fail("Broken CLI must not be reinstalled"))
    monkeypatch.setattr(
        setup.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], returncode, stdout, "failed")
    )
    assert setup.prepare(str(binary), install_missing=True)["reason"] == "startup_failed"


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
def test_official_installer_invocation(monkeypatch, platform):
    monkeypatch.setattr(setup.sys, "platform", platform)
    monkeypatch.setattr(setup.shutil, "which", lambda name: name)
    downloads = []
    scripts = []

    def download(request, **kwargs):
        downloads.append(request.full_url)
        assert request.get_header("User-agent") == "memu-cli"
        assert kwargs["timeout"] == 30
        return io.BytesIO(b"official installer fixture")

    def execute(argv, **kwargs):
        script = Path(argv[-1])
        assert script.read_bytes() == b"official installer fixture"
        scripts.append(script)
        assert kwargs["timeout"] == 300
        assert kwargs["check"] is True
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["env"]["CODEX_NON_INTERACTIVE"] == "1"
        if platform == "win32":
            assert argv[:6] == [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
            ]
        else:
            assert argv[0] == "sh"
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(setup.urllib.request, "urlopen", download)
    monkeypatch.setattr(setup.subprocess, "run", execute)
    setup._install()
    extension = "ps1" if platform == "win32" else "sh"
    assert downloads == [f"https://chatgpt.com/codex/install.{extension}"]
    assert not scripts[0].exists()


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
def test_default_installation_directory(monkeypatch, tmp_path, platform):
    monkeypatch.setattr(setup.sys, "platform", platform)
    monkeypatch.delenv("CODEX_INSTALL_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(setup.Path, "home", lambda: tmp_path)
    expected = tmp_path / ("Programs/OpenAI/Codex/bin" if platform == "win32" else ".local/bin")
    assert setup._installation_directory() == expected
    monkeypatch.setenv("CODEX_INSTALL_DIR", str(tmp_path / "custom"))
    assert setup._installation_directory() == tmp_path / "custom"


@pytest.mark.parametrize("content", [b"", b"x" * (1024 * 1024 + 1)], ids=["empty", "oversized"])
def test_invalid_download_never_executes(monkeypatch, content):
    monkeypatch.setattr(setup.shutil, "which", lambda name: name)
    monkeypatch.setattr(setup.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(content))
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k: pytest.fail("Invalid download must not execute"))
    with pytest.raises(ValueError, match="empty or exceeds"):
        setup._install()


def test_version_timeout_returns_failure(environment, monkeypatch, capsys):
    binary = environment / "selected"
    binary.touch()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 20)

    monkeypatch.setattr(setup.subprocess, "run", timeout)
    assert main(["prepare-cli", "--codex", str(binary), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_cli_success_reports_executable_readiness(environment, capsys):
    binary = environment / "selected"
    binary.touch()
    assert main(["prepare-cli", "--codex", str(binary), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["stage"] == "host_executable"
    assert result["version"] == "codex-cli 0.163.0"


def test_official_download_http_failure_reports_status(environment, monkeypatch):
    def download():
        raise urllib.error.HTTPError("https://chatgpt.com/codex/install.ps1", 403, "Forbidden", Message(), None)

    monkeypatch.setattr(setup, "_install", download)
    result = setup.prepare(install_missing=True)
    assert result["status"] == "failed"
    assert result["reason"] == "download_http_error"
    assert result["http_status"] == 403
    assert "HTTP 403 (Forbidden)" in result["detail"]


@pytest.mark.parametrize(
    "bundle",
    [
        "AppData/Local/OpenAI/Codex/bin/build-id/codex.exe",
        "WindowsApps/OpenAI.Codex_1.0_x64/package/codex.exe",
        "Applications/Codex.app/Contents/Resources/codex",
    ],
)
def test_desktop_bundle_is_not_a_standalone_cli(environment, monkeypatch, bundle):
    binary = environment / bundle
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(setup.shutil, "which", lambda name, **kw: None if kw else str(binary))
    assert setup.prepare()["reason"] == "missing"
    assert setup.prepare(str(binary))["status"] == "failed"


def test_official_installation_wins_over_desktop_path(environment, monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "win32")
    binary = environment / "codex.exe"
    binary.touch()
    monkeypatch.setattr(
        setup.shutil, "which", lambda *a, **kw: "C:/Users/test/AppData/Local/OpenAI/Codex/bin/build/codex.exe"
    )
    assert setup.prepare()["executable"] == str(binary.resolve())


def test_searches_path_after_excluding_desktop(environment, monkeypatch):
    binary = environment / "tools/codex.exe"
    binary.parent.mkdir()
    binary.touch()
    desktop = environment / "AppData/Local/OpenAI/Codex/bin/build/codex.exe"
    monkeypatch.setattr(setup.shutil, "which", lambda name, **kw: str(binary) if kw else str(desktop))
    assert setup.prepare()["executable"] == str(binary.resolve())


def test_desktop_only_environment_installs_standalone_cli(environment, monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "win32")
    desktop = environment / "AppData/Local/OpenAI/Codex/bin/build/codex.exe"
    monkeypatch.setattr(setup.shutil, "which", lambda name, **kw: None if kw else str(desktop))
    calls = []

    def install():
        calls.append("installed")
        (environment / "codex.exe").touch()

    monkeypatch.setattr(setup, "_install", install)
    result = setup.prepare(install_missing=True)
    assert result["status"] == "passed"
    assert result["executable"] == str((environment / "codex.exe").resolve())
    assert calls == ["installed"]


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_runtime_find_uses_unix_official_directory(tmp_path, monkeypatch, platform):
    monkeypatch.setattr(setup, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(setup.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("CODEX_INSTALL_DIR", raising=False)
    binary = tmp_path / ".local/bin/codex"
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(setup.shutil, "which", lambda *a, **kw: pytest.fail("Official directory precedes PATH"))
    assert setup.find_executable() == binary.resolve()


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
def test_path_alias_to_desktop_does_not_hide_later_standalone(environment, monkeypatch, platform):
    monkeypatch.setattr(setup, "sys", SimpleNamespace(platform=platform))
    name = "codex.exe" if platform == "win32" else "codex"
    alias = environment / "desktop-alias"
    tools = environment / "tools"
    desktop = environment / "Applications/Codex.app/Contents/Resources" / name
    binary = tools / name
    tools.mkdir()
    binary.touch()
    resolve = Path.resolve

    def resolve_alias(path, *args, **kwargs):
        return desktop if path == alias / name else resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve_alias)
    monkeypatch.setattr(setup.os, "get_exec_path", lambda: [str(alias), str(tools)])

    def which(command, path=None):
        assert command == "codex"
        return str(alias / name) if path is None or str(alias) in path else str(binary)

    monkeypatch.setattr(setup.shutil, "which", which)
    assert setup.find_executable() == resolve(binary)
