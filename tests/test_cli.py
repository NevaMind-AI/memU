"""CLI surface tests: argument parsing, config mapping, and error paths.

These never construct a MemoryService (no network, no embedding calls); they
exercise the pure argv -> config layer and the pre-service validation in the
handlers.
"""

from __future__ import annotations

import pathlib

import pytest

from memu.cli import build_parser, main
from memu.env import database_config


def test_parser_covers_all_entry_points() -> None:
    parser = build_parser()
    for argv in (
        ["retrieve", "query"],
        ["search", "query"],
        ["list-files"],
        ["commit", "payload.json"],
    ):
        args = parser.parse_args(argv)
        assert callable(args.handler)


def test_database_config_dispatch(tmp_path: pathlib.Path) -> None:
    assert database_config(":memory:") == {"metadata_store": {"provider": "inmemory"}}
    pg = database_config("postgresql://u:p@localhost/db")
    assert pg["metadata_store"]["provider"] == "postgres"
    assert pg["metadata_store"]["dsn"] == "postgresql://u:p@localhost/db"

    db_file = tmp_path / "nested" / "memu.sqlite3"
    sqlite = database_config(str(db_file))
    assert sqlite["metadata_store"]["provider"] == "sqlite"
    assert sqlite["metadata_store"]["dsn"] == f"sqlite:///{db_file}"
    assert db_file.parent.is_dir()  # parent directory is created eagerly

    # A full SQLite URL passes through untouched; treating it as a bare path
    # would double-prefix it into sqlite:///sqlite:////... and silently split
    # the store in two. INSTALL.md's example MEMU_DB is exactly this shape.
    url = database_config("sqlite:////Users/x/.memu/memu.sqlite3")
    assert url["metadata_store"]["dsn"] == "sqlite:////Users/x/.memu/memu.sqlite3"


def test_commit_missing_payload_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["commit", "/definitely/not/a/payload.json"]) == 2
    assert "no such file" in capsys.readouterr().err
