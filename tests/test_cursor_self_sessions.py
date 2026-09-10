"""Cursor's scheduled bridging run must not mine its own transcript."""

from __future__ import annotations

import pathlib
from argparse import Namespace
from dataclasses import replace

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging import self_sessions
from memu.hosts.bridging.layout import Layout
from memu.hosts.cursor.cli import SESSION_ID_ENV
from memu.hosts.cursor.cli import SPEC as CURSOR_SPEC
from memu.hosts.cursor.sessions import CursorTranscriptSource


def test_cursor_declares_its_conversation_id_variable() -> None:
    """Cursor Agent 2026.08.04 passes this request-scoped id to shell tools."""
    assert CURSOR_SPEC.session_id_env == SESSION_ID_ENV == "CURSOR_CONVERSATION_ID"


def test_cursor_transcript_name_is_its_conversation_id(tmp_path: pathlib.Path) -> None:
    conversation_id = "6ea28aed-874f-44e1-9dd2-d8ad0b1bbc85"
    transcript = tmp_path / "project" / "agent-transcripts" / conversation_id / f"{conversation_id}.jsonl"

    assert CursorTranscriptSource(tmp_path).session_id(transcript) == conversation_id


@pytest.mark.parametrize("marked", [False, True])
async def test_only_an_os_marked_cursor_run_claims_its_session(
    marked: bool,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    conversation_id = "6ea28aed-874f-44e1-9dd2-d8ad0b1bbc85"
    captured: dict[str, object] = {}

    class ExistingCursorSource(CursorTranscriptSource):
        def exists(self) -> bool:
            return True

    spec = replace(CURSOR_SPEC, source_factory=ExistingCursorSource)

    async def fake_prepare(*args: object, **kwargs: object) -> int:
        captured["skip_sessions"] = kwargs["skip_sessions"]
        return 0

    monkeypatch.setattr(host_cli, "prepare", fake_prepare)
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda spec: None)
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)
    monkeypatch.setattr(host_cli.Path, "cwd", lambda: tmp_path / "project")
    monkeypatch.setenv(SESSION_ID_ENV, conversation_id)
    if marked:
        monkeypatch.setenv(self_sessions.BRIDGING_RUN_ENV, "1")
    else:
        monkeypatch.delenv(self_sessions.BRIDGING_RUN_ENV, raising=False)

    base = tmp_path / "memu-cursor"
    rc = await host_cli._cmd_prepare(
        spec,
        Namespace(session_dir=str(tmp_path / "sessions"), base_dir=str(base), max_jobs=10),
    )

    expected = [conversation_id] if marked else []
    assert rc == 0
    assert "prepared 0 session(s) -> 0 job(s)" in capsys.readouterr().out
    assert captured["skip_sessions"] == expected
    assert self_sessions.load(Layout(base=base, host="cursor").self_sessions) == expected


def test_cursor_unix_wrapper_exports_the_bridging_marker() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/cursor/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )

    assert f"export {self_sessions.BRIDGING_RUN_ENV}=1" in doc
