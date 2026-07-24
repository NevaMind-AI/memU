"""CLI surface tests: argument parsing, config mapping, and error paths.

These never construct a MemoryService (no network, no embedding calls); they
exercise the pure argv -> config layer and the pre-service validation in the
handlers.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from memu import cli
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


def test_commit_forwards_user_and_resources(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "user": {"user_id": "u1", "agent_id": "a1"},
        "recall_files": [{"name": "profile"}],
        "resource": [{"path": "/workspace/notes.md"}],
    }
    path = tmp_path / "payload.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    received: dict[str, Any] = {}

    class Backend:
        async def commit_results(self, **kwargs: Any) -> dict[str, Any]:
            received.update(kwargs)
            return {"recall_files": [], "resources": []}

    monkeypatch.setattr(cli, "build_agentic_memory_backend_from_env", lambda **kwargs: Backend())

    assert main(["commit", str(path)]) == 0
    assert received == {
        "recall_files": payload["recall_files"],
        "resource": payload["resource"],
        "user": payload["user"],
    }


def test_retrieve_and_list_files_use_selected_backend(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, Any]] = []

    class Backend:
        async def progressive_retrieve(self, query: str) -> dict[str, Any]:
            calls.append(("retrieve", query))
            return {"segments": [], "files": [], "resources": []}

        async def list_all_recall_files(self) -> dict[str, Any]:
            calls.append(("list", None))
            return {"categories": []}

    backend = Backend()
    monkeypatch.setattr(cli, "build_agentic_memory_backend_from_env", lambda **kwargs: backend)

    assert main(["retrieve", "tea"]) == 0
    assert main(["list-files"]) == 0
    assert calls == [("retrieve", "tea"), ("list", None)]
    assert "0 recall file(s)" in capsys.readouterr().out
