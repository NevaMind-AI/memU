from __future__ import annotations

import pytest

from memu.hosts.hooks import CodexNotifyHook


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
