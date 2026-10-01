"""Prepare must not call an unrecognized transcript format a quiet day."""

from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from dataclasses import replace
from pathlib import Path

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging import pipeline
from memu.hosts.generic.cli import SPEC as GENERIC_SPEC
from memu.hosts.openclaw.cli import SPEC as OPENCLAW_SPEC


class EmptyRecallService:
    async def list_all_recall_files(self, *args: object, **kwargs: object) -> dict[str, object]:
        return {"recall_files": [], "next_cursor": None}


@pytest.fixture(autouse=True)
def _offline_prepare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: EmptyRecallService())
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda spec: None)
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)


async def _prepare(root: Path, base: Path) -> int:
    return await host_cli._cmd_prepare(
        GENERIC_SPEC,
        Namespace(session_dir=str(root), base_dir=str(base), max_jobs=10),
    )


async def test_prepare_warns_when_sessions_contain_no_recognized_records(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "agent"
    root.mkdir()
    (root / "metrics.jsonl").write_text('{"event":"boot","ms":12}\n', encoding="utf-8")

    assert await _prepare(root, tmp_path / "base") == 0

    captured = capsys.readouterr()
    assert "found 1 session(s)" in captured.err
    assert "recognized 0 conversation/tool record(s)" in captured.err
    assert f"memu-agent detect {root}" in captured.err
    assert "no new session turns" not in captured.out


async def test_prepare_repeats_the_warning_while_the_format_is_unrecognized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "agent"
    root.mkdir()
    (root / "metrics.jsonl").write_text('{"event":"boot","ms":12}\n', encoding="utf-8")
    base = tmp_path / "base"

    assert await _prepare(root, base) == 0
    first = capsys.readouterr().err
    assert "recognized 0 conversation/tool record(s)" in first

    assert await _prepare(root, base) == 0
    second = capsys.readouterr().err
    assert "recognized 0 conversation/tool record(s)" in second


async def test_prepare_with_no_sessions_remains_a_quiet_day(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "agent"
    root.mkdir()

    assert await _prepare(root, tmp_path / "base") == 0

    captured = capsys.readouterr()
    assert "no new session turns since the last run; nothing to mine" in captured.out
    assert "recognized 0 conversation/tool record(s)" not in captured.err


async def test_prepare_with_seen_recognized_records_is_not_a_format_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "agent"
    root.mkdir()
    session = root / "session.jsonl"
    session.write_text(json.dumps({"role": "user", "content": "hello"}) + "\n", encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    (base / ".session_manifest.agent.json").write_text(json.dumps({"session.jsonl": {"lines": 1}}), encoding="utf-8")

    assert await _prepare(root, base) == 0

    captured = capsys.readouterr()
    assert "no new session turns since the last run; nothing to mine" in captured.out
    assert "recognized 0 conversation/tool record(s)" not in captured.err


def _openclaw_store(
    root: Path,
    *,
    event_json: str | None,
    event_zstd: bytes | None = None,
) -> Path:
    db = root / "main" / "agent" / "openclaw-agent.sqlite"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE session_windows (
          session_id TEXT PRIMARY KEY,
          transcript_updated_at INTEGER
        );
        CREATE TABLE transcript_events (
          session_id TEXT NOT NULL,
          seq INTEGER NOT NULL,
          event_json TEXT,
          created_at INTEGER NOT NULL,
          event_zstd BLOB,
          event_utf8_bytes INTEGER,
          navigation_json TEXT,
          PRIMARY KEY (session_id, seq),
          CHECK (
            (event_json IS NOT NULL AND event_zstd IS NULL)
            OR (
              event_json IS NULL AND event_zstd IS NOT NULL
              AND event_utf8_bytes IS NOT NULL
              AND navigation_json IS NOT NULL
            )
          )
        );
        CREATE TABLE transcript_rewrite_watermarks (
          session_id TEXT PRIMARY KEY,
          generation TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO session_windows (session_id, transcript_updated_at) VALUES (?, ?)",
        ("s1", 1_785_308_110_945),
    )
    conn.execute(
        "INSERT INTO transcript_events "
        "(session_id, seq, event_json, created_at, event_zstd, event_utf8_bytes, navigation_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "s1",
            0,
            event_json,
            1_785_308_110_945,
            event_zstd,
            128 if event_zstd is not None else None,
            '{"kind":"message"}' if event_zstd is not None else None,
        ),
    )
    conn.execute(
        "INSERT INTO transcript_rewrite_watermarks (session_id, generation, updated_at) VALUES (?, ?, ?)",
        ("s1", "generation-1", 1_785_308_110_945),
    )
    conn.commit()
    conn.close()
    return db


async def _prepare_openclaw(root: Path, base: Path) -> int:
    spec = replace(OPENCLAW_SPEC, resolve_self_sessions=lambda source, layout: [])
    return await host_cli._cmd_prepare(
        spec,
        Namespace(session_dir=str(root), base_dir=str(base), max_jobs=10),
    )


async def test_openclaw_sqlite_only_after_jsonl_disappears_still_prepares(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "agents"
    _openclaw_store(
        root,
        event_json=json.dumps({"type": "message", "message": {"role": "user", "content": "remember"}}),
    )
    legacy = root / "main" / "sessions" / "s1.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("stale duplicate\n", encoding="utf-8")
    legacy.unlink()

    base = tmp_path / "base"
    assert await _prepare_openclaw(root, base) == 0

    captured = capsys.readouterr()
    assert list((base / "jobs").glob("*.txt"))
    assert "recognized 0 conversation/tool record(s)" not in captured.err
    assert "no new session turns" not in captured.out


async def test_openclaw_compressed_transcript_warns_instead_of_reporting_quiet_day(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "agents"
    _openclaw_store(root, event_json=None, event_zstd=b"compressed-event")

    assert await _prepare_openclaw(root, tmp_path / "base") == 0

    captured = capsys.readouterr()
    assert "found 1 session(s) for OpenClaw" in captured.err
    assert "recognized 0 conversation/tool record(s)" in captured.err
    assert "no new session turns" not in captured.out
