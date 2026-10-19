from __future__ import annotations

from types import SimpleNamespace

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.hooks import CodexNotifyHook, HeadlessAgent, run_agent


def test_diagnostic_agent_output_is_tee_written(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("memu.hosts.hooks.shutil.which", lambda _: "codex")
    monkeypatch.setattr(
        "memu.hosts.hooks.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout="agent stdout\n", stderr="agent stderr\n", returncode=0),
    )
    layout = Layout.default("codex", tmp_path / "memu")
    layout.base.mkdir()

    run_agent(HeadlessAgent(("codex",)), layout, diagnostic=True)

    captured = capsys.readouterr()
    log = (layout.base / "hook.log").read_text()
    assert "agent stdout" in captured.out
    assert "agent stderr" in captured.err
    assert "agent stdout" in log
    assert "agent stderr" in log


def test_codex_notify_hook_installs_and_removes_its_own_command(tmp_path):
    config = tmp_path / "config.toml"
    hook = CodexNotifyHook(config)
    argv = ["memu-codex", "hook"]

    hook.install(argv)
    assert config.read_text() == 'notify = ["memu-codex", "hook"]\n'

    hook.remove("memu-codex")
    assert config.read_text() == ""


def test_codex_notify_hook_does_not_overwrite_existing_notify(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('notify = ["existing-notifier"]\n')

    with pytest.raises(ValueError, match="already defines notify"):
        CodexNotifyHook(config).install(["memu-codex", "hook"])

    assert config.read_text() == 'notify = ["existing-notifier"]\n'
