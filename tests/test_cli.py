"""CLI surface tests: argument parsing, config mapping, and error paths.

These never construct a MemoryService (no network, no LLM); they exercise the
pure argv -> config layer and the pre-service validation in the handlers.
"""

from __future__ import annotations

import pathlib

import pytest

from memu.cli import _database_config, build_parser, main


def test_parser_covers_all_entry_points() -> None:
    parser = build_parser()
    for argv in (
        ["memorize", "notes.md"],
        ["memorize-workspace", "./ws"],
        ["sync", "./ws"],
        ["retrieve", "query"],
        ["retrieve-workspace", "query"],
        ["search", "query"],
        ["export"],
    ):
        args = parser.parse_args(argv)
        assert callable(args.handler)


def test_database_config_dispatch(tmp_path: pathlib.Path) -> None:
    assert _database_config(":memory:") == {"metadata_store": {"provider": "inmemory"}}
    pg = _database_config("postgresql://u:p@localhost/db")
    assert pg["metadata_store"]["provider"] == "postgres"
    assert pg["metadata_store"]["dsn"] == "postgresql://u:p@localhost/db"

    db_file = tmp_path / "nested" / "memu.sqlite3"
    sqlite = _database_config(str(db_file))
    assert sqlite["metadata_store"]["provider"] == "sqlite"
    assert sqlite["metadata_store"]["dsn"] == f"sqlite:///{db_file}"
    assert db_file.parent.is_dir()  # parent directory is created eagerly


def test_memorize_missing_file_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["memorize", "/definitely/not/a/file.md"]) == 2
    assert "no such file" in capsys.readouterr().err


def test_memorize_unknown_extension_exits_2(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "data.xyz"
    target.write_text("hello")
    assert main(["memorize", str(target)]) == 2
    assert "cannot infer modality" in capsys.readouterr().err


def test_memorize_workspace_missing_folder_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["memorize-workspace", "/definitely/not/a/folder"]) == 2
    assert "no such folder" in capsys.readouterr().err
