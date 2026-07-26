"""Shared test fixtures.

Default every test to the *embedded* instruction templates. Two isolations, both
autouse so a test never has to remember them: no test reaches the network for a
template (``MEMU_TEMPLATE_BASE_URL`` blanked switches the fetch off), and no test
reads or writes the real ``~/.memu`` template cache (redirected under ``tmp_path``).
The handful of tests that exercise the fetch/cache path re-enable the base URL and
stub ``urlopen`` themselves — the later ``setenv`` on the same monkeypatch wins.
"""

from __future__ import annotations

import pathlib

import pytest

from memu.hosts import templates


@pytest.fixture(autouse=True)
def _offline_templates(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("MEMU_TEMPLATE_BASE_URL", "")
    monkeypatch.setattr(templates, "_cache_dir", lambda: tmp_path / "template-cache")
