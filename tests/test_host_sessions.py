"""Each host's record seam: does classify() slice its log the way that host writes it?

One test module per invariant class, five hosts. The fixtures are hand-written
records in each host's real on-disk shape (see the session-location table in ADR
0010); if a host changes its log format, the fixture — not the pipeline — is what
these tests localize the break to.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

from memu.hosts.base import RecordKind
from memu.hosts.claude_code.sessions import ClaudeCodeTranscriptSource
from memu.hosts.codex.sessions import CodexTranscriptSource
from memu.hosts.cursor.sessions import CursorTranscriptSource
from memu.hosts.hermes.sessions import HermesTranscriptSource
from memu.hosts.openclaw.sessions import OpenClawTranscriptSource


def _line(entry: dict) -> str:
    return json.dumps(entry)


# ── Codex ──────────────────────────────────────────────────────────────────────


def test_codex_classify() -> None:
    source = CodexTranscriptSource()
    assert source.classify(_line({"payload": {"type": "message", "role": "user"}})) is RecordKind.MESSAGE
    assert source.classify(_line({"payload": {"type": "function_call", "name": "shell"}})) is RecordKind.TOOL
    assert source.classify(_line({"payload": {"type": "reasoning"}})) is RecordKind.OTHER


# ── Claude Code ────────────────────────────────────────────────────────────────


def test_claude_code_classify_conversation_turns() -> None:
    source = ClaudeCodeTranscriptSource()
    user = {"type": "user", "message": {"role": "user", "content": "fix the bug"}}
    assistant = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": "On it."}]},
    }
    assert source.classify(_line(user)) is RecordKind.MESSAGE
    assert source.classify(_line(assistant)) is RecordKind.MESSAGE


def test_claude_code_classify_tool_records() -> None:
    """Claude Code logs a tool's result as a *user*-typed record — the block type,
    not the role, is what classifies."""
    source = ClaudeCodeTranscriptSource()
    tool_use = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "input": {}}]},
    }
    tool_result = {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }
    assert source.classify(_line(tool_use)) is RecordKind.TOOL
    assert source.classify(_line(tool_result)) is RecordKind.TOOL


def test_claude_code_classify_multi_block_records() -> None:
    """Real logs carry multi-block records; a ``text`` block wins (see the class
    docstring). Pinned so a refactor that inspects only ``content[0]`` — which
    would pass every single-block fixture above — fails here instead of silently
    losing records: ``thinking`` precedes ``tool_use`` inside real records, so
    first-block logic would bucket them OTHER and the tool call would vanish
    from the skill transcript. Cursor's narrated_tool test cannot catch this;
    each host has its own classify.
    """
    source = ClaudeCodeTranscriptSource()
    narrated_tool = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Running the build."},
                {"type": "tool_use", "name": "Bash", "input": {"command": "make"}},
            ],
        },
    }
    thinking_then_tool = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "hmm"},
                {"type": "tool_use", "name": "Bash", "input": {}},
            ],
        },
    }
    # Prose sharing a record with the tool calls it narrates stays conversation.
    assert source.classify(_line(narrated_tool)) is RecordKind.MESSAGE
    # No prose: the tool call must survive as TOOL even with thinking in front.
    assert source.classify(_line(thinking_then_tool)) is RecordKind.TOOL


def test_claude_code_drops_noise() -> None:
    source = ClaudeCodeTranscriptSource()
    thinking = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": "hmm"}]},
    }
    meta = {"type": "user", "isMeta": True, "message": {"role": "user", "content": "<harness-injected>"}}
    queue = {"type": "queue-operation", "operation": "enqueue", "content": "next prompt"}
    assert source.classify(_line(thinking)) is RecordKind.OTHER
    assert source.classify(_line(meta)) is RecordKind.OTHER
    assert source.classify(_line(queue)) is RecordKind.OTHER
    assert source.classify("not json") is RecordKind.OTHER


# ── Cursor ─────────────────────────────────────────────────────────────────────


def test_cursor_classify() -> None:
    source = CursorTranscriptSource()
    user = {"role": "user", "message": {"content": [{"type": "text", "text": "upload to github"}]}}
    narrated_tool = {
        "role": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "Running git."},
                {"type": "tool_use", "name": "Shell", "input": {"command": "git push"}},
            ]
        },
    }
    bare_tool = {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": "Shell", "input": {}}]}}
    assert source.classify(_line(user)) is RecordKind.MESSAGE
    # Prose sharing a record with the tool calls it narrates stays conversation.
    assert source.classify(_line(narrated_tool)) is RecordKind.MESSAGE
    assert source.classify(_line(bare_tool)) is RecordKind.TOOL
    assert source.classify(_line({"role": "system"})) is RecordKind.OTHER


def test_cursor_discovers_only_agent_transcripts(tmp_path: pathlib.Path) -> None:
    """The project dirs also hold canvases and terminal logs — those must not be mined."""
    transcript = tmp_path / "Users-a-proj" / "agent-transcripts" / "abc" / "abc.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text('{"role":"user","message":{"content":[{"type":"text","text":"hi"}]}}\n', encoding="utf-8")
    stray = tmp_path / "Users-a-proj" / "terminals" / "log.jsonl"
    stray.parent.mkdir(parents=True)
    stray.write_text("{}\n", encoding="utf-8")

    assert CursorTranscriptSource(tmp_path).discover() == [transcript]


# ── OpenClaw ───────────────────────────────────────────────────────────────────


def test_openclaw_classify() -> None:
    source = OpenClawTranscriptSource()
    user = {"type": "message", "timestamp": 1752537600000, "message": {"role": "user", "content": "hi"}}
    assistant = {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "hey"}]}}
    tool = {"type": "message", "message": {"role": "toolResult", "content": [{"type": "text", "text": "ok"}]}}
    header = {"type": "session", "id": "s1", "cwd": "/home/user/proj"}
    compaction = {"type": "compaction", "firstKeptEntryId": "e9"}
    assert source.classify(_line(user)) is RecordKind.MESSAGE
    assert source.classify(_line(assistant)) is RecordKind.MESSAGE
    assert source.classify(_line(tool)) is RecordKind.TOOL
    assert source.classify(_line(header)) is RecordKind.OTHER
    assert source.classify(_line(compaction)) is RecordKind.OTHER


def test_openclaw_timestamp_accepts_iso_and_epoch_millis() -> None:
    source = OpenClawTranscriptSource()
    iso = {"type": "message", "timestamp": "2026-07-15T00:00:00Z", "message": {"role": "user", "content": "hi"}}
    millis = {"type": "message", "timestamp": 1752537600000, "message": {"role": "user", "content": "hi"}}
    assert source.timestamp(_line(iso)) == "2026-07-15T00:00:00Z"
    assert source.timestamp(_line(millis)) == "2025-07-15T00:00:00+00:00"


# ── Hermes ─────────────────────────────────────────────────────────────────────


def _hermes_db(tmp_path: pathlib.Path) -> pathlib.Path:
    db = tmp_path / "state.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE sessions (id TEXT PRIMARY KEY);
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            tool_call_id TEXT,
            tool_calls TEXT,
            tool_name TEXT,
            timestamp REAL NOT NULL
        );
        """
    )
    rows = [
        ("old", "user", "earlier session", None, None, None, 100.0),
        ("new", "system", "you are hermes", None, None, None, 200.0),
        ("new", "user", "delete the temp files", None, None, None, 201.0),
        ("new", "assistant", None, None, '[{"name":"shell"}]', None, 202.0),
        ("new", "tool", "removed 3 files", "call_1", None, "shell", 203.0),
        ("new", "assistant", "Done — removed 3 files.", None, None, None, 204.0),
    ]
    conn.executemany(
        "INSERT INTO messages (session_id, role, content, tool_call_id, tool_calls, tool_name, timestamp)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db


def test_hermes_discovers_sessions_most_recent_first(tmp_path: pathlib.Path) -> None:
    source = HermesTranscriptSource(_hermes_db(tmp_path))
    assert source.exists()
    assert [source.key(path) for path in source.discover()] == ["new", "old"]


def test_hermes_reads_and_classifies_rows(tmp_path: pathlib.Path) -> None:
    source = HermesTranscriptSource(_hermes_db(tmp_path))
    (session,) = [path for path in source.discover() if source.key(path) == "new"]

    records = source.read_records(session)
    kinds = [source.classify(record) for record in records]
    assert kinds == [
        RecordKind.OTHER,  # system prompt
        RecordKind.MESSAGE,  # user turn
        RecordKind.TOOL,  # assistant tool_calls, no prose
        RecordKind.TOOL,  # tool output
        RecordKind.MESSAGE,  # assistant answer
    ]
    assert source.timestamp(records[1]) == "1970-01-01T00:03:21+00:00"


def test_hermes_missing_db_is_empty_not_an_error(tmp_path: pathlib.Path) -> None:
    source = HermesTranscriptSource(tmp_path / "state.db")
    assert not source.exists()
    assert source.discover() == []
