"""Malformed block or role metadata must not halt pi, Cursor or WorkBuddy transcript preparation."""

import json
import pathlib

from memu.hosts.base import RecordKind
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.hosts.cursor.sessions import CursorTranscriptSource
from memu.hosts.pi.sessions import PiTranscriptSource
from memu.hosts.workbuddy.sessions import WorkBuddyTranscriptSource


def _pi(content: object, role: object = "assistant") -> str:
    return json.dumps({"type": "message", "message": {"role": role, "content": content}})


def _cursor(blocks: list[dict[str, object]]) -> str:
    return json.dumps({"role": "assistant", "message": {"content": blocks}})


def _workbuddy(blocks: list[dict[str, object]]) -> str:
    return json.dumps({"type": "message", "role": "assistant", "content": blocks})


def test_pi_ignores_unhashable_block_types_and_roles() -> None:
    source = PiTranscriptSource()
    assert source.classify(_pi([{"type": ["text"]}])) is RecordKind.OTHER
    assert source.classify(_pi([{"type": ["text"]}, {"type": "toolCall"}])) is RecordKind.TOOL
    assert (
        source.classify(_pi([{"type": {"unexpected": "text"}}, {"type": "text", "text": "hi"}])) is RecordKind.MESSAGE
    )
    assert source.classify(_pi([{"type": "text", "text": "hi"}], role=["assistant"])) is RecordKind.OTHER


def test_cursor_ignores_unhashable_block_types() -> None:
    source = CursorTranscriptSource()
    assert source.classify(_cursor([{"type": ["text"]}])) is RecordKind.OTHER
    assert source.classify(_cursor([{"type": ["text"]}, {"type": "tool_use"}])) is RecordKind.TOOL
    assert (
        source.classify(_cursor([{"type": {"unexpected": "text"}}, {"type": "text", "text": "hi"}]))
        is RecordKind.MESSAGE
    )


def test_workbuddy_ignores_unhashable_block_types() -> None:
    source = WorkBuddyTranscriptSource()
    assert source.classify(_workbuddy([{"type": ["output_text"]}])) is RecordKind.OTHER
    assert (
        source.classify(_workbuddy([{"type": ["output_text"]}, {"type": "output_text", "text": "hi"}]))
        is RecordKind.MESSAGE
    )


def test_malformed_record_does_not_abort_prepare(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "cursor"
    transcript = root / "project" / "agent-transcripts" / "session.jsonl"
    transcript.parent.mkdir(parents=True)
    good = json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "hi"}]}})
    transcript.write_text(good + "\n" + _cursor([{"type": ["text"]}]) + "\n", encoding="utf-8")

    prepared = prepare_transcripts(
        CursorTranscriptSource(root),
        out_dir=tmp_path / "sessions",
        manifest_path=tmp_path / "manifest.json",
        max_jobs=10,
        pending_path=tmp_path / "pending.json",
    )

    assert prepared == 1
    assert (tmp_path / "sessions" / "1.jsonl").read_text(encoding="utf-8").splitlines() == [good]
