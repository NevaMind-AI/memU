"""Shared test fixtures.

Default every test to the *embedded* instruction templates. Two isolations, both
autouse so a test never has to remember them: no test reaches the network for a
template (``MEMU_TEMPLATE_BASE_URL`` blanked switches the fetch off), and no test
reads or writes the real ``~/.memu`` template cache (redirected under ``tmp_path``).
The handful of tests that exercise the fetch/cache path re-enable the base URL and
stub ``urlopen`` themselves — the later ``setenv`` on the same monkeypatch wins.

Event reporting gets the same treatment, for a sharper reason: the suite exercises
whole CLI commands, several of which now record events, and a test run must never
POST telemetry to the real endpoint or write to the developer's own
``~/.memu/config.env`` and spool.
"""

from __future__ import annotations

import pathlib

import pytest

from memu.hosts import templates


@pytest.fixture(autouse=True)
def _offline_templates(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("MEMU_TEMPLATE_BASE_URL", "")
    monkeypatch.setattr(templates, "_cache_dir", lambda: tmp_path / "template-cache")


@pytest.fixture(autouse=True)
def _offline_events(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """No test reports an event, and none touches the real spool or config.

    Blanking the base URL is what actually disables reporting; the redirected
    spool and config are for the tests that re-enable it deliberately, so they
    still cannot reach the developer's home directory. Tests that want reporting
    on re-``setenv`` the base URL — the later call on the same monkeypatch wins.
    """
    monkeypatch.setenv("MEMU_EVENTS_BASE_URL", "")
    monkeypatch.setenv("MEMU_EVENTS_SPOOL", str(tmp_path / "events" / "events.jsonl"))
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(tmp_path / "events" / "config.env"))
