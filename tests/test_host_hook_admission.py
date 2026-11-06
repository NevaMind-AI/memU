"""Host workers share admission mechanics while preserving their state paths."""

from __future__ import annotations

import json

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.codex import notify_console
from memu.hosts.hooks import admission


@pytest.mark.parametrize("host", ["codex", "claude-code"])
def test_admission_uses_host_state_and_existing_workspace_lock(tmp_path, monkeypatch, host):
    monkeypatch.setattr(admission.time, "time", lambda: 36000.0)
    layout = Layout.default(host, tmp_path)
    state = tmp_path / f".memorize_last_started.{host}.json"
    with notify_console._workspace_lock(tmp_path) as acquired:
        assert acquired
        with admission.memorize_run(layout) as admitted:
            assert not admitted
    assert not state.exists()
    with admission.memorize_run(layout) as admitted:
        assert admitted
        assert json.loads(state.read_text()) == 36000.0
        with notify_console._workspace_lock(tmp_path) as acquired:
            assert not acquired
    with admission.memorize_run(layout) as admitted:
        assert not admitted
    other_host = "claude-code" if host == "codex" else "codex"
    with admission.memorize_run(Layout.default(other_host, tmp_path)) as admitted:
        assert admitted


def test_failed_state_write_releases_lock_without_admission(tmp_path, monkeypatch):
    state = tmp_path / ".memorize_last_started.claude-code.json"
    state.write_text("0")

    def fail(*_):
        raise OSError("synthetic write failure")  # noqa: TRY003

    monkeypatch.setattr(admission, "_atomic_write_text", fail)
    with (
        pytest.raises(OSError, match="synthetic write failure"),
        admission.memorize_run(Layout.default("claude-code", tmp_path)),
    ):
        pytest.fail("must not admit before persisting cooldown")
    assert state.read_text() == "0"
    with admission.workspace_lock(tmp_path) as acquired:
        assert acquired
