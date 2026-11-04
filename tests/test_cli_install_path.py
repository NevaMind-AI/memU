"""User PATH setup is isolated from registry writes in CI."""

import os
from types import SimpleNamespace

import pytest

from memu.hosts import cli_install


@pytest.mark.parametrize("configured", [False, True])
def test_windows_path_preserves_existing_entries_and_updates_process(tmp_path, monkeypatch, configured):
    monkeypatch.setattr(cli_install, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(cli_install.shutil, "which", lambda _: "powershell.exe")
    executable = tmp_path / "claude.exe"
    previous = str(tmp_path) + os.pathsep + "other-bin" if configured else "other-bin"
    monkeypatch.setenv("PATH", previous)
    calls = []

    def run(argv, **kwargs):
        assert argv[:4] == ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"]
        assert "SetEnvironmentVariable('Path', $updated, 'User')" in argv[4]
        assert "$entries -notcontains" in argv[4]
        assert kwargs["env"]["MEMU_CLI_BIN"] == str(tmp_path)
        assert kwargs["check"] is True
        calls.append(argv)

    monkeypatch.setattr(cli_install.subprocess, "run", run)
    cli_install.configure_windows_path(executable)
    assert os.environ["PATH"] == (previous if configured else str(tmp_path) + os.pathsep + previous)
    assert len(calls) == 1


def test_unix_path_setup_is_left_to_official_installer(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_install, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(cli_install.subprocess, "run", lambda *a, **k: pytest.fail("Windows setup on Unix"))
    cli_install.configure_windows_path(tmp_path / "claude")
