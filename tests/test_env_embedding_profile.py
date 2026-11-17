"""``MEMU_EMBED_BATCH_SIZE`` bounds each provider embedding request.

Field origin: DashScope's OpenAI-compatible embedding endpoint rejects batches
larger than 10, while memU's provider default is 64. Host installs need a way
to lower the batch without changing code.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest

from memu import env as menv

VARS = (
    "MEMU_EMBED_BATCH_SIZE",
    "MEMU_EMBED_PROVIDER",
    "MEMU_LLM_PROVIDER",
    "MEMU_EMBED_MODEL",
    "MEMU_BASE_URL",
    "MEMU_API_KEY",
)


@pytest.fixture()
def config_file(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    cfg = tmp_path / "config.env"
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(cfg))
    for var in VARS:
        monkeypatch.delenv(var, raising=False)
    menv.reload()
    yield cfg
    menv.reload()


def test_batch_size_read_from_config(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_EMBED_BATCH_SIZE=10\n")
    menv.reload()

    assert menv.embedding_profile()["embed_batch_size"] == 10


def test_environment_batch_size_wins(config_file: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_EMBED_BATCH_SIZE", "10")
    config_file.write_text("MEMU_EMBED_BATCH_SIZE=64\n")
    menv.reload()

    assert menv.embedding_profile()["embed_batch_size"] == 10


def test_invalid_batch_size_is_rejected(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_EMBED_BATCH_SIZE=0\n")
    menv.reload()

    with pytest.raises(menv.ConfigError, match="MEMU_EMBED_BATCH_SIZE"):
        menv.embedding_profile()


def test_absent_batch_size_leaves_provider_default(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_DB=/tmp/x.sqlite3\n")
    menv.reload()

    assert "embed_batch_size" not in menv.embedding_profile()
