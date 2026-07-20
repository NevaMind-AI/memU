"""``config.env`` is "the carrier" — for ``NO_PROXY`` too.

Field origin: a live OpenClaw install wrote ``NO_PROXY`` into ``config.env``,
found it inert (memU only consumed ``MEMU_*`` keys), and had to bake the
variable into the scheduled prompt's shell commands — which the guides forbid
(nothing machine-specific in the prompt). These pin the fix: passthrough keys
in the file reach ``os.environ`` (without overriding it), and the
``MEMU_HTTP_PROXY`` escape hatch works from the file, not only from the shell.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from memu import env as menv
from memu.embedding.http_client import _load_proxy

PROXY = "http://proxy.corp:8080"


@pytest.fixture()
def config_file(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    for key in list(os.environ):
        if key.lower().endswith("_proxy") or key.lower() == "no_proxy":
            monkeypatch.delenv(key, raising=False)
    cfg = tmp_path / "config.env"
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(cfg))
    menv.reload()
    yield cfg
    # The passthrough writes os.environ outside monkeypatch's bookkeeping —
    # undo by hand so nothing leaks into other test modules.
    for key in menv._ENV_PASSTHROUGH:
        os.environ.pop(key, None)
    menv.reload()


def test_no_proxy_in_config_reaches_the_environment(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_DB=/data/x.sqlite3\nNO_PROXY=localhost,127.0.0.1\n")
    menv.reload()

    assert menv.env("MEMU_DB") == "/data/x.sqlite3"  # touching the file loads it
    assert os.environ["NO_PROXY"] == "localhost,127.0.0.1"


def test_environment_wins_over_the_file(config_file: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_PROXY", "already-set")
    config_file.write_text("NO_PROXY=from-file\n")
    menv.reload()

    menv.env("MEMU_DB")
    assert os.environ["NO_PROXY"] == "already-set"


def test_no_passthrough_keys_no_side_effect(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_DB=/data/x.sqlite3\n")
    menv.reload()

    menv.env("MEMU_DB")
    assert "NO_PROXY" not in os.environ


def test_memu_http_proxy_works_from_the_file(config_file: pathlib.Path) -> None:
    """The escape hatch (#519) must not require a shell export — the scheduled
    task has no shell, the file is all it has."""
    config_file.write_text(f"MEMU_HTTP_PROXY={PROXY}\n")
    menv.reload()

    assert _load_proxy("http://localhost:11434/v1") == PROXY
