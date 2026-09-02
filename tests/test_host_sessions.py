"""Each host's record seam: does classify() slice its log the way that host writes it?

The fixtures are hand-written
records in each host's real on-disk shape (see the session-location table in ADR
0010); if a host changes its log format, the fixture — not the pipeline — is what
these tests localize the break to.
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3

import pytest

from memu.hosts.base import RecordKind, TranscriptReadError
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.hosts.claude_code.sessions import ClaudeCodeTranscriptSource
from memu.hosts.codex.sessions import CodexTranscriptSource
from memu.hosts.cola.sessions import ColaTranscriptSource
from memu.hosts.cursor.sessions import CursorTranscriptSource
from memu.hosts.hermes.sessions import HermesTranscriptSource, state_db_path
from memu.hosts.openclaw.sessions import OpenClawTranscriptSource
from memu.hosts.pi.sessions import PiTranscriptSource
from memu.hosts.workbuddy.sessions import WorkBuddyTranscriptSource


def _line(entry: dict) -> str:
    return json.dumps(entry)


# ── pi ────────────────────────────────────────────────────────────────────────


def test_pi_classifies_conversation_and_tool_rows() -> None:
    source = PiTranscriptSource()
    user = {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}}
    narrated_tool = {
        "type": "message",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Running it."}, {"type": "toolCall", "name": "bash"}],
        },
    }
    tool_call = {
        "type": "message",
        "message": {
            "role": "assistant",
            "content": [{"type": "thinking", "thinking": "hmm"}, {"type": "toolCall", "name": "bash"}],
        },
    }
    tool_result = {"type": "message", "message": {"role": "toolResult", "content": []}}
    bash_execution = {"type": "message", "message": {"role": "bashExecution", "command": "pwd"}}

    assert source.classify(_line(user)) is RecordKind.MESSAGE
    assert source.classify(_line(narrated_tool)) is RecordKind.MESSAGE
    assert source.classify(_line(tool_call)) is RecordKind.TOOL
    assert source.classify(_line(tool_result)) is RecordKind.TOOL
    assert source.classify(_line(bash_execution)) is RecordKind.TOOL


def test_pi_drops_v3_metadata_and_thinking_only_rows() -> None:
    source = PiTranscriptSource()
    assert source.classify(_line({"type": "session", "version": 3, "id": "s", "cwd": "/workspace"})) is RecordKind.OTHER
    assert source.classify(_line({"type": "compaction", "summary": "old work"})) is RecordKind.OTHER
    assert (
        source.classify(_line({"type": "message", "message": {"role": "assistant", "content": [{"type": "thinking"}]}}))
        is RecordKind.OTHER
    )
    assert source.classify("not json") is RecordKind.OTHER


def test_pi_discovers_sessions_across_encoded_working_directories(tmp_path: pathlib.Path) -> None:
    older = tmp_path / "--Users-a-one--" / "older.jsonl"
    newer = tmp_path / "--Users-a-two--" / "newer.jsonl"
    older.parent.mkdir()
    newer.parent.mkdir()
    older.write_text("{}\n", encoding="utf-8")
    newer.write_text("{}\n", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))
    assert PiTranscriptSource(tmp_path).discover() == [newer, older]


def test_pi_session_id_matches_the_exported_uuid(tmp_path: pathlib.Path) -> None:
    source = PiTranscriptSource(tmp_path)
    transcript = tmp_path / "2026-09-02T10-31-41-043Z_01a061ac-aaf3-7f05-a295-d95115fef655.jsonl"

    assert source.session_id(transcript) == "01a061ac-aaf3-7f05-a295-d95115fef655"


# ── Cola ──────────────────────────────────────────────────────────────────────


def test_cola_classifies_message_and_tool_rows() -> None:
    source = ColaTranscriptSource()
    user = {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}}
    assistant = {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}}
    tool_call = {"type": "message", "message": {"role": "assistant", "content": [{"type": "toolCall"}]}}
    tool_result = {"type": "message", "message": {"role": "toolResult", "content": [{"type": "text", "text": "ok"}]}}
    assert source.classify(_line(user)) is RecordKind.MESSAGE
    assert source.classify(_line(assistant)) is RecordKind.MESSAGE
    assert source.classify(_line(tool_call)) is RecordKind.TOOL
    assert source.classify(_line(tool_result)) is RecordKind.TOOL


def test_cola_drops_runtime_metadata_and_reads_nested_timestamp() -> None:
    source = ColaTranscriptSource()
    metadata = {"type": "model_change", "timestamp": "2026-07-26T09:37:18.122Z"}
    message = {
        "type": "message",
        "message": {
            "role": "user",
            "timestamp": "2026-07-26T09:37:18.124Z",
            "content": [{"type": "text", "text": "hi"}],
        },
    }
    assert source.classify(_line(metadata)) is RecordKind.OTHER
    assert source.timestamp(_line(message)) == "2026-07-26T09:37:18.124Z"


def test_cola_discovers_scope_transcripts(tmp_path: pathlib.Path) -> None:
    transcript = tmp_path / "desktop-local" / "session.jsonl"
    transcript.parent.mkdir()
    transcript.write_text('{"type":"message"}\n', encoding="utf-8")
    assert ColaTranscriptSource(tmp_path).discover() == [transcript]


# ── Codex ──────────────────────────────────────────────────────────────────────


def test_codex_classify() -> None:
    source = CodexTranscriptSource()
    assert source.classify(_line({"payload": {"type": "message", "role": "user"}})) is RecordKind.MESSAGE
    assert source.classify(_line({"payload": {"type": "function_call", "name": "shell"}})) is RecordKind.TOOL
    assert source.classify(_line({"payload": {"type": "reasoning"}})) is RecordKind.OTHER


def _codex_user(*texts: str) -> str:
    content = [{"type": "input_text", "text": text} for text in texts]
    return _line({"type": "response_item", "payload": {"type": "message", "role": "user", "content": content}})


def test_codex_classify_drops_injected_user_records() -> None:
    """Codex has no isMeta flag: environment context, abort markers, and
    AGENTS.md dumps are logged as ordinary user messages, distinguishable from
    typing only by their leading marker. The layout drifts across versions —
    0.80.0 writes standalone records, 0.124.x packs AGENTS.md and
    environment_context into one record's items — so all four shapes observed
    in real logs are pinned here (#510). Role-only classify would feed every
    one of them to the mining jobs as something the user said.
    """
    source = CodexTranscriptSource()
    env = _codex_user("<environment_context>\n  <cwd>D:\\proj</cwd>\n</environment_context>")
    agents_md = _codex_user("# AGENTS.md instructions for D:\\proj\n\n<INSTRUCTIONS>reply in haiku</INSTRUCTIONS>")
    aborted = _codex_user("<turn_aborted>\nThe user interrupted the previous turn on purpose.\n</turn_aborted>")
    packed = _codex_user("# AGENTS.md instructions for D:\\proj", "<environment_context>\n</environment_context>")
    assert source.classify(env) is RecordKind.OTHER
    assert source.classify(agents_md) is RecordKind.OTHER
    assert source.classify(aborted) is RecordKind.OTHER
    assert source.classify(packed) is RecordKind.OTHER


def test_codex_injected_filter_never_costs_a_real_message() -> None:
    """The filter fails open: one item of real prose keeps the record, markers
    mid-text don't count, and assistant records are never inspected."""
    source = CodexTranscriptSource()
    assistant = {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "<environment_context> is injected by the harness."}],
        },
    }
    assert source.classify(_codex_user("fix the bug")) is RecordKind.MESSAGE
    assert (
        source.classify(_codex_user("fix the bug", "<environment_context></environment_context>")) is RecordKind.MESSAGE
    )
    assert source.classify(_codex_user("what does <environment_context> mean?")) is RecordKind.MESSAGE
    assert source.classify(_line(assistant)) is RecordKind.MESSAGE


def test_codex_sanitize_filters_known_private_fields_and_keeps_unknown_ones(tmp_path: pathlib.Path) -> None:
    source = CodexTranscriptSource()
    metadata = {"turn_id": "private-turn", "futureMetadataField": "private-with-container"}
    image = {
        "type": "input_image",
        "image_url": "data:image/png;base64,content",
        "detail": "auto",
        "futureContentField": "preserved",
    }
    message = {
        "timestamp": "2026-09-01T12:00:00Z",
        "type": "response_item",
        "futureTopLevel": "preserved",
        "payload": {
            "type": "message",
            "id": "message-id",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Done."}, image],
            "phase": "final_answer",
            "internal_chat_message_metadata_passthrough": metadata,
            "futurePayloadField": "preserved",
        },
    }
    tool_call = {
        "timestamp": "2026-09-01T12:00:01Z",
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "id": "call-item-id",
            "name": "shell",
            "arguments": '{"command":"pwd"}',
            "call_id": "call-id",
            "internal_chat_message_metadata_passthrough": metadata,
        },
    }
    tool_output = {
        "timestamp": "2026-09-01T12:00:02Z",
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "id": "output-item-id",
            "call_id": "call-id",
            "output": "D:/private",
            "internal_chat_message_metadata_passthrough": metadata,
        },
    }

    assert json.loads(source.sanitize(tmp_path / "session.jsonl", _line(message))) == {
        "type": "response_item",
        "futureTopLevel": "preserved",
        "payload": {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Done."}, image],
            "phase": "final_answer",
            "futurePayloadField": "preserved",
        },
    }
    assert json.loads(source.sanitize(tmp_path / "session.jsonl", _line(tool_call))) == {
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "shell",
            "arguments": '{"command":"pwd"}',
            "call_id": "call-id",
        },
    }
    assert json.loads(source.sanitize(tmp_path / "session.jsonl", _line(tool_output))) == {
        "type": "response_item",
        "payload": {"type": "function_call_output", "call_id": "call-id", "output": "D:/private"},
    }

    untouched = '{"type": "response_item", "payload": {"type": "message", "role": "user"}}'
    assert source.sanitize(tmp_path / "session.jsonl", untouched) == untouched
    assert source.sanitize(tmp_path / "session.jsonl", "not json") == "not json"
    assert source.sanitize(tmp_path / "session.jsonl", "[]") == "[]"


def test_codex_prepare_sanitizes_output_without_changing_cursor(tmp_path: pathlib.Path) -> None:
    session = tmp_path / "rollout-2026-09-01T12-00-00-session-id.jsonl"
    metadata = {"turn_id": "private-turn"}
    records = [
        {
            "timestamp": "2026-09-01T12:00:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "message-id",
                "role": "user",
                "content": [{"type": "input_text", "text": "remember this"}],
                "internal_chat_message_metadata_passthrough": metadata,
            },
        },
        {
            "timestamp": "2026-09-01T12:00:01Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "id": "call-item-id",
                "name": "shell",
                "arguments": '{"command":"pwd"}',
                "call_id": "call-id",
                "internal_chat_message_metadata_passthrough": metadata,
            },
        },
        {
            "timestamp": "2026-09-01T12:00:02Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "id": "output-item-id",
                "call_id": "call-id",
                "output": "D:/private",
                "internal_chat_message_metadata_passthrough": metadata,
            },
        },
    ]
    raw = "\n".join(_line(record) for record in records) + "\n"
    session.write_text(raw, encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    pending = tmp_path / "pending.json"
    out_dir = tmp_path / "out"

    assert prepare_transcripts(CodexTranscriptSource(tmp_path), out_dir, manifest, 10, pending) == 1

    memory = [json.loads(line) for line in (out_dir / "1.jsonl").read_text(encoding="utf-8").splitlines()]
    full = [json.loads(line) for line in (out_dir / "1_full.jsonl").read_text(encoding="utf-8").splitlines()]
    assert memory == [
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "remember this"}],
            },
        }
    ]
    assert full == [
        *memory,
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "shell",
                "arguments": '{"command":"pwd"}',
                "call_id": "call-id",
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "function_call_output", "call_id": "call-id", "output": "D:/private"},
        },
    ]
    assert session.read_text(encoding="utf-8") == raw
    assert json.loads(pending.read_text(encoding="utf-8"))[session.name] == {
        "lines": 3,
        "last_timestamp": "2026-09-01T12:00:02Z",
    }


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


def test_claude_code_sanitize_filters_known_private_fields_and_keeps_unknown_ones(tmp_path: pathlib.Path) -> None:
    source = ClaudeCodeTranscriptSource()
    content = [
        {
            "type": "tool_use",
            "name": "Bash",
            "input": {"command": "pytest"},
            "futureBlockField": {"preserved": True},
        }
    ]
    record = {
        "type": "assistant",
        "uuid": "record-id",
        "timestamp": "2026-08-31T12:00:00Z",
        "cwd": "D:/private",
        "sessionId": "session-id",
        "permissionMode": "default",
        "toolUseResult": {"stdout": "private"},
        "futureTopLevel": "preserved",
        "message": {
            "id": "message-id",
            "type": "message",
            "role": "assistant",
            "model": "private-model",
            "usage": {"input_tokens": 1},
            "content": content,
            "futureMessageField": "preserved",
        },
    }

    assert json.loads(source.sanitize(tmp_path / "session.jsonl", _line(record))) == {
        "type": "assistant",
        "futureTopLevel": "preserved",
        "message": {
            "type": "message",
            "role": "assistant",
            "content": content,
            "futureMessageField": "preserved",
        },
    }
    assert source.sanitize(tmp_path / "session.jsonl", "not json") == "not json"
    assert source.sanitize(tmp_path / "session.jsonl", "[]") == "[]"


def test_claude_code_prepare_sanitizes_output_without_changing_cursor(tmp_path: pathlib.Path) -> None:
    session = tmp_path / "session.jsonl"
    records = [
        {
            "type": "user",
            "timestamp": "2026-08-31T12:00:00Z",
            "uuid": "user-id",
            "message": {"role": "user", "content": "remember this", "id": "message-id"},
        },
        {
            "type": "assistant",
            "timestamp": "2026-08-31T12:00:01Z",
            "toolUseResult": {"stdout": "private"},
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "pwd"}}],
                "usage": {"input_tokens": 1},
            },
        },
        {
            "type": "user",
            "timestamp": "2026-08-31T12:00:02Z",
            "sessionId": "private-session",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "D:/private"}],
                "id": "message-id",
            },
        },
    ]
    raw = "\n".join(_line(record) for record in records) + "\n"
    session.write_text(raw, encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    pending = tmp_path / "pending.json"
    out_dir = tmp_path / "out"

    assert prepare_transcripts(ClaudeCodeTranscriptSource(tmp_path), out_dir, manifest, 10, pending) == 1

    memory = [json.loads(line) for line in (out_dir / "1.jsonl").read_text(encoding="utf-8").splitlines()]
    full = [json.loads(line) for line in (out_dir / "1_full.jsonl").read_text(encoding="utf-8").splitlines()]
    assert memory == [{"type": "user", "message": {"role": "user", "content": "remember this"}}]
    assert full == [
        *memory,
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "pwd"}}],
            },
        },
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "content": "D:/private"}]},
        },
    ]
    assert session.read_text(encoding="utf-8") == raw
    assert json.loads(pending.read_text(encoding="utf-8"))["session.jsonl"] == {
        "lines": 3,
        "last_timestamp": "2026-08-31T12:00:02Z",
    }


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


def test_openclaw_sanitize_filters_known_runtime_fields_and_keeps_unknown_ones(tmp_path: pathlib.Path) -> None:
    source = OpenClawTranscriptSource()
    record = {
        "type": "message",
        "id": "entry-id",
        "parentId": "parent-id",
        "timestamp": "2026-09-01T00:00:00Z",
        "futureTopLevel": "preserved",
        "message": {
            "role": "assistant",
            "timestamp": "2026-09-01T00:00:00Z",
            "api": "private-api",
            "provider": "private-provider",
            "model": "private-model",
            "usage": {"input": 1},
            "stopReason": "toolUse",
            "responseId": "private-response",
            "idempotencyKey": "private-key",
            "__openclaw": {"private": True},
            "openclawDeliveryMirror": {"private": True},
            "futureMessageField": "preserved",
            "content": [
                {"type": "text", "text": "hello", "textSignature": "private", "futureTextField": "preserved"},
                {
                    "type": "toolCall",
                    "id": "call-id",
                    "name": "exec",
                    "arguments": {"command": "pwd"},
                    "partialArgs": "private",
                    "futureToolField": "preserved",
                },
            ],
        },
    }

    assert json.loads(source.sanitize(tmp_path / "session.jsonl", _line(record))) == {
        "type": "message",
        "futureTopLevel": "preserved",
        "message": {
            "role": "assistant",
            "futureMessageField": "preserved",
            "content": [
                {"type": "text", "text": "hello", "futureTextField": "preserved"},
                {
                    "type": "toolCall",
                    "id": "call-id",
                    "name": "exec",
                    "arguments": {"command": "pwd"},
                    "futureToolField": "preserved",
                },
            ],
        },
    }


def test_openclaw_prepare_sanitizes_stored_output_without_changing_cursor(tmp_path: pathlib.Path) -> None:
    entry = {
        "type": "message",
        "id": "entry-id",
        "parentId": "parent-id",
        "timestamp": "2026-09-01T00:00:00Z",
        "message": {
            "role": "toolResult",
            "timestamp": "2026-09-01T00:00:00Z",
            "toolCallId": "call-id",
            "toolName": "exec",
            "isError": False,
            "details": {"cwd": "/private", "exitCode": 0},
            "content": [{"type": "text", "text": "ok", "textSignature": "private"}],
        },
    }
    _openclaw_store(tmp_path, "main", {"s1": [(0, entry, 1_788_220_800_000)]})
    source = OpenClawTranscriptSource(tmp_path)

    prepared, out_dir, pending = _prepare_openclaw(source, tmp_path, {})

    assert prepared == 1
    assert (out_dir / "1.jsonl").read_text(encoding="utf-8") == "\n"
    assert [json.loads(line) for line in (out_dir / "1_full.jsonl").read_text(encoding="utf-8").splitlines()] == [
        {
            "type": "message",
            "message": {
                "role": "toolResult",
                "toolCallId": "call-id",
                "toolName": "exec",
                "isError": False,
                "content": [{"type": "text", "text": "ok"}],
            },
        }
    ]
    assert pending["main/sessions/s1.jsonl"] == {
        "container": "sqlite",
        "generation": "generation-s1",
        "lines": 1,
        "last_timestamp": "2026-09-01T00:00:00Z",
    }


def test_openclaw_timestamp_accepts_iso_and_epoch_millis() -> None:
    source = OpenClawTranscriptSource()
    iso = {"type": "message", "timestamp": "2026-07-15T00:00:00Z", "message": {"role": "user", "content": "hi"}}
    millis = {"type": "message", "timestamp": 1752537600000, "message": {"role": "user", "content": "hi"}}
    assert source.timestamp(_line(iso)) == "2026-07-15T00:00:00Z"
    assert source.timestamp(_line(millis)) == "2025-07-15T00:00:00+00:00"


def test_openclaw_discovers_only_main_session_transcripts(tmp_path: pathlib.Path) -> None:
    """Trajectory sidecars hold trace events (all-OTHER: an empty transcript
    that still occupies a prepare slot and still spawns mining jobs); checkpoint
    sidecars re-emit turns the session file already has (the same conversation
    mined twice). On the surveyed live host, 51 of 60 discovered files were
    sidecars and 46 of 69 user-role messages were checkpoint duplicates."""
    sessions = tmp_path / "main" / "sessions"
    sessions.mkdir(parents=True)
    session = sessions / "a83c9e20-072d-4708-902a-47c596b14d55.jsonl"
    session.write_text('{"type":"message"}\n', encoding="utf-8")
    trajectory = sessions / "a83c9e20-072d-4708-902a-47c596b14d55.trajectory.jsonl"
    trajectory.write_text("{}\n", encoding="utf-8")
    checkpoint = sessions / "c22ca449-d54c-4dd0-89ee-17cbf7af90f0.checkpoint.20d27d05.jsonl"
    checkpoint.write_text("{}\n", encoding="utf-8")

    assert OpenClawTranscriptSource(tmp_path).discover() == [session]


# ── OpenClaw, SQLite session store ────────────────────────────────────────────
#
# Upstream moved transcripts out of the JSONL files into one database per agent.
# The fixtures below are the real schema (STRICT tables, the session_windows
# foreign key, the separate trajectory table) so that a future upstream change
# breaks the fixture rather than the pipeline.


def _openclaw_store(
    root: pathlib.Path,
    agent_id: str,
    events: dict[str, list[tuple[int, dict, int]]],
    *,
    empty_sessions: tuple[str, ...] = (),
    trajectory: tuple[str, ...] = (),
    generations: dict[str, str] | None = None,
    activity: dict[str, int] | None = None,
) -> pathlib.Path:
    """One agent's transcript database, in the layout OpenClaw writes it to.

    ``events`` maps session id to ``(seq, entry, created_at_millis)`` rows.
    """
    db = root / agent_id / "agent" / "openclaw-agent.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE session_windows (
          session_id TEXT PRIMARY KEY,
          session_key TEXT,
          reason TEXT,
          transcript_updated_at INTEGER
        ) STRICT;
        CREATE TABLE transcript_events (
          session_id TEXT NOT NULL,
          seq INTEGER NOT NULL,
          event_json TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          PRIMARY KEY (session_id, seq),
          FOREIGN KEY (session_id) REFERENCES "session_windows"(session_id) ON DELETE CASCADE
        ) STRICT;
        CREATE TABLE transcript_rewrite_watermarks (
          session_id TEXT NOT NULL PRIMARY KEY,
          generation TEXT NOT NULL,
          updated_at INTEGER NOT NULL,
          FOREIGN KEY (session_id) REFERENCES "session_windows"(session_id) ON DELETE CASCADE
        ) STRICT;
        CREATE TABLE trajectory_runtime_events (
          session_id TEXT NOT NULL,
          seq INTEGER NOT NULL,
          event_json TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          PRIMARY KEY (session_id, seq)
        ) STRICT;
        """
    )
    if generations is None:
        generations = {session_id: f"generation-{session_id}" for session_id in events}
    activity = activity or {}
    for session_id in (*events, *empty_sessions, *trajectory):
        rows = events.get(session_id, [])
        fallback_activity = max((created_at for _, _, created_at in rows), default=None)
        conn.execute(
            "INSERT OR IGNORE INTO session_windows "
            "(session_id, session_key, reason, transcript_updated_at) VALUES (?, ?, NULL, ?)",
            (session_id, f"agent:{agent_id}:main", activity.get(session_id, fallback_activity)),
        )
    for session_id, rows in events.items():
        conn.executemany(
            "INSERT INTO transcript_events (session_id, seq, event_json, created_at) VALUES (?, ?, ?, ?)",
            [(session_id, seq, json.dumps(entry), created_at) for seq, entry, created_at in rows],
        )
    for session_id, generation in generations.items():
        conn.execute(
            "INSERT INTO transcript_rewrite_watermarks (session_id, generation, updated_at) VALUES (?, ?, ?)",
            (session_id, generation, activity.get(session_id, 1785377019307)),
        )
    for session_id in trajectory:
        conn.execute(
            "INSERT INTO trajectory_runtime_events (session_id, seq, event_json, created_at) VALUES (?, 0, ?, ?)",
            (session_id, json.dumps({"type": "trace"}), 1785377019307),
        )
    conn.commit()
    conn.close()
    return db


def _openclaw_turn(role: str, text: str) -> dict:
    return {"type": "message", "id": text, "message": {"role": role, "content": text}}


def test_openclaw_discovers_stored_sessions_most_recent_first(tmp_path: pathlib.Path) -> None:
    _openclaw_store(
        tmp_path,
        "main",
        {
            "older": [(0, _openclaw_turn("user", "first"), 1785308110945)],
            "newer": [(0, _openclaw_turn("user", "second"), 1785379402605)],
        },
    )
    source = OpenClawTranscriptSource(tmp_path)

    assert source.exists()
    assert [source.key(path) for path in source.discover()] == [
        "main/sessions/newer.jsonl",
        "main/sessions/older.jsonl",
    ]


def test_openclaw_stored_session_keeps_the_legacy_cursor_key(tmp_path: pathlib.Path) -> None:
    """The upgrade must not re-mine anything. The legacy file name *was* the
    session id, so a stored session is addressed exactly as its file was — a
    session mined to N records as a file resumes at N+1 as rows, with no manifest
    migration and no flag day."""
    session_id = "a83c9e20-072d-4708-902a-47c596b14d55"
    _openclaw_store(tmp_path, "main", {session_id: [(0, _openclaw_turn("user", "hi"), 1785308110945)]})

    (path,) = OpenClawTranscriptSource(tmp_path).discover()
    assert OpenClawTranscriptSource(tmp_path).key(path) == f"main/sessions/{session_id}.jsonl"


def test_openclaw_reads_stored_events_in_sequence_order(tmp_path: pathlib.Path) -> None:
    """``event_json`` is the entry verbatim — the same string that was one line
    of the file — so classify() needs no container-specific branch."""
    _openclaw_store(
        tmp_path,
        "main",
        {
            "s1": [
                (0, {"type": "session", "id": "s1", "cwd": "/w"}, 1785308110945),
                (1, _openclaw_turn("user", "delete the temp files"), 1785308110946),
                (2, _openclaw_turn("assistant", "on it"), 1785308110947),
                (3, _openclaw_turn("toolResult", "removed 3 files"), 1785308110948),
                (4, {"type": "reset", "reason": "new", "firstKeptEntryId": "e9"}, 1785308110949),
            ]
        },
    )
    source = OpenClawTranscriptSource(tmp_path)
    (path,) = source.discover()

    records = source.read_records(path)
    assert [source.classify(record) for record in records] == [
        RecordKind.OTHER,  # session header
        RecordKind.MESSAGE,  # user turn
        RecordKind.MESSAGE,  # assistant turn
        RecordKind.TOOL,  # tool output
        RecordKind.OTHER,  # reset marker
    ]
    assert json.loads(records[1])["message"]["content"] == "delete the temp files"


def test_openclaw_merges_both_shapes_on_one_time_scale(tmp_path: pathlib.Path) -> None:
    """A host that upgraded keeps its old files, so both shapes coexist — and
    they count time differently: the store in epoch *milliseconds*, files in
    st_mtime *seconds*. Compared raw, every stored session sorts ahead of every
    file and prepare's early stop then hides real sessions behind them."""
    _openclaw_store(tmp_path, "main", {"stored-old": [(0, _openclaw_turn("user", "a"), 1_600_000_000_000)]})
    legacy = tmp_path / "main" / "sessions" / "file-new.jsonl"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(_line(_openclaw_turn("user", "b")) + "\n", encoding="utf-8")
    os.utime(legacy, (1_700_000_000, 1_700_000_000))  # newer than the stored session

    source = OpenClawTranscriptSource(tmp_path)
    assert [source.key(path) for path in source.discover()] == [
        "main/sessions/file-new.jsonl",
        "main/sessions/stored-old.jsonl",
    ]


def test_openclaw_store_wins_over_a_leftover_file(tmp_path: pathlib.Path) -> None:
    """Same session in both containers is one conversation on one cursor key.
    The store is the live one; the file stopped being appended to at the upgrade."""
    session_id = "a83c9e20-072d-4708-902a-47c596b14d55"
    _openclaw_store(tmp_path, "main", {session_id: [(0, _openclaw_turn("user", "from the store"), 1785308110945)]})
    stale = tmp_path / "main" / "sessions" / f"{session_id}.jsonl"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text(_line(_openclaw_turn("user", "from the file")) + "\n", encoding="utf-8")

    source = OpenClawTranscriptSource(tmp_path)
    (path,) = source.discover()  # not two entries
    (record,) = source.read_records(path)
    assert json.loads(record)["message"]["content"] == "from the store"


def test_openclaw_reads_a_file_whose_session_is_not_in_the_store(tmp_path: pathlib.Path) -> None:
    """Mid-migration, or a file the import never took: the store exists but does
    not hold this session, so the file is still the only copy of it."""
    _openclaw_store(tmp_path, "main", {"imported": [(0, _openclaw_turn("user", "a"), 1785308110945)]})
    orphan = tmp_path / "main" / "sessions" / "never-imported.jsonl"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text(_line(_openclaw_turn("user", "only on disk")) + "\n", encoding="utf-8")

    source = OpenClawTranscriptSource(tmp_path)
    (path,) = [candidate for candidate in source.discover() if candidate.name == "never-imported.jsonl"]
    (record,) = source.read_records(path)
    assert json.loads(record)["message"]["content"] == "only on disk"


def test_openclaw_skips_sessions_with_no_transcript_events(tmp_path: pathlib.Path) -> None:
    """Grouping over the events themselves is what keeps empty sessions out of
    prepare's slots — the #533 failure, avoided by construction rather than by a
    name filter. Trajectory events cannot resurrect one: they live in their own
    table, unreachable from the one we select from."""
    _openclaw_store(
        tmp_path,
        "main",
        {"real": [(0, _openclaw_turn("user", "hi"), 1785308110945)]},
        empty_sessions=("slash-command-only",),
        trajectory=("trace-only",),
    )
    source = OpenClawTranscriptSource(tmp_path)

    assert [source.key(path) for path in source.discover()] == ["main/sessions/real.jsonl"]


def test_openclaw_skips_the_sqlite_import_archive(tmp_path: pathlib.Path) -> None:
    """``doctor`` moves imported legacy files here. Their turns are already being
    read out of the store under the pre-upgrade cursor key, so discovering them at
    their new path would re-mine the whole pre-upgrade history under a second key."""
    _openclaw_store(tmp_path, "main", {"imported": [(0, _openclaw_turn("user", "hi"), 1785308110945)]})
    archived = tmp_path / "main" / "session-sqlite-import-archive" / "imported.jsonl"
    archived.parent.mkdir(parents=True, exist_ok=True)
    archived.write_text(_line(_openclaw_turn("user", "hi")) + "\n", encoding="utf-8")

    source = OpenClawTranscriptSource(tmp_path)
    assert [source.key(path) for path in source.discover()] == ["main/sessions/imported.jsonl"]


def test_openclaw_discovers_every_agents_store(tmp_path: pathlib.Path) -> None:
    """One database per agent, so discovery is per agent directory."""
    _openclaw_store(tmp_path, "main", {"s-main": [(0, _openclaw_turn("user", "a"), 1785308110945)]})
    _openclaw_store(tmp_path, "second", {"s-second": [(0, _openclaw_turn("user", "b"), 1785379402605)]})

    source = OpenClawTranscriptSource(tmp_path)
    assert [source.key(path) for path in source.discover()] == [
        "second/sessions/s-second.jsonl",
        "main/sessions/s-main.jsonl",
    ]


def test_openclaw_opens_the_store_read_only(tmp_path: pathlib.Path) -> None:
    """The gateway and live sessions share this database in WAL mode — the
    bridging task must never take its write lock. As with Hermes, the path is
    percent-escaped into the URI: pasted in raw, a '%' would decode and a '#'
    would truncate it, silently dropping ?mode=ro."""
    import pytest

    weird = tmp_path / "pct %41 #frag"
    weird.mkdir()
    db = _openclaw_store(weird, "main", {"s1": [(0, _openclaw_turn("user", "hi"), 1785308110945)]})
    source = OpenClawTranscriptSource(weird)

    assert [source.key(path) for path in source.discover()] == ["main/sessions/s1.jsonl"]
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        source._connect(db).execute(
            "INSERT INTO transcript_events (session_id, seq, event_json, created_at) VALUES ('x', 0, '{}', 1)"
        )


def test_openclaw_unreadable_store_contributes_nothing_rather_than_raising(tmp_path: pathlib.Path) -> None:
    """prepare runs unattended on a schedule. A store that is corrupt, or on a
    schema this adapter does not recognize, has to degrade to "no sessions here" —
    a crash would stop mining silently until someone noticed. The legacy files
    beside it must still be read."""
    db = tmp_path / "main" / "agent" / "openclaw-agent.sqlite"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"this is not a database")
    legacy = tmp_path / "main" / "sessions" / "still-here.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(_line(_openclaw_turn("user", "hi")) + "\n", encoding="utf-8")

    source = OpenClawTranscriptSource(tmp_path)
    assert [source.key(path) for path in source.discover()] == ["main/sessions/still-here.jsonl"]
    assert source.read_records(legacy) == [_line(_openclaw_turn("user", "hi"))]


def test_openclaw_failed_stored_session_read_does_not_fall_back_to_virtual_file(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A database-held session has only a virtual legacy path. A read error is
    not an empty query result and must never try to open that nonexistent file."""
    _openclaw_store(tmp_path, "main", {"stored-only": [(0, _openclaw_turn("user", "hi"), 1785308110945)]})
    source = OpenClawTranscriptSource(tmp_path)
    (session,) = source.discover()
    monkeypatch.setattr(
        source,
        "_connect",
        lambda db: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")),
    )

    with pytest.raises(TranscriptReadError, match="database is locked"):
        source.read_records(session)


def test_openclaw_prepare_warns_and_continues_after_stored_session_read_error(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """One transient SQLite failure must not crash unattended prepare or trigger
    the early stop before a healthy older session."""
    _openclaw_store(
        tmp_path,
        "main",
        {
            "broken-new": [(0, _openclaw_turn("user", "broken"), 1_800_000_000_000)],
            "healthy-old": [(0, _openclaw_turn("user", "healthy"), 1_700_000_000_000)],
        },
    )
    source = OpenClawTranscriptSource(tmp_path)
    query = source._query

    def fail_one_session(db: pathlib.Path, sql: str, *args: object) -> list[tuple]:
        if args == ("broken-new",):
            error = sqlite3.OperationalError("database is locked")
            raise TranscriptReadError(db, error) from error
        return query(db, sql, *args)

    monkeypatch.setattr(source, "_query", fail_one_session)
    out_dir = tmp_path / "out"

    prepared = prepare_transcripts(
        source,
        out_dir=out_dir,
        manifest_path=tmp_path / "manifest.json",
        max_jobs=10,
        pending_path=tmp_path / "pending.json",
    )

    assert prepared == 1
    assert "healthy" in (out_dir / "1.jsonl").read_text(encoding="utf-8")
    assert "broken-new" in caplog.text
    assert "database is locked" in caplog.text


def test_openclaw_missing_generation_is_a_recoverable_read_error(tmp_path: pathlib.Path) -> None:
    _openclaw_store(
        tmp_path,
        "main",
        {"s1": [(0, _openclaw_turn("user", "hi"), 1785308110945)]},
        generations={},
    )
    source = OpenClawTranscriptSource(tmp_path)
    (session,) = source.discover()

    with pytest.raises(TranscriptReadError, match="missing transcript generation"):
        source.read_incremental(session, None)


def _prepare_openclaw(
    source: OpenClawTranscriptSource,
    tmp_path: pathlib.Path,
    manifest: dict[str, dict[str, object]],
) -> tuple[int, pathlib.Path, dict[str, dict[str, object]]]:
    manifest_path = tmp_path / "manifest.json"
    pending_path = tmp_path / "pending.json"
    out_dir = tmp_path / "out"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    prepared = prepare_transcripts(
        source,
        out_dir=out_dir,
        manifest_path=manifest_path,
        max_jobs=10,
        pending_path=pending_path,
    )
    return prepared, out_dir, json.loads(pending_path.read_text(encoding="utf-8"))


def test_openclaw_same_generation_emits_only_appended_rows(tmp_path: pathlib.Path) -> None:
    events = [(seq, _openclaw_turn("user", f"turn-{seq}"), 1785308110945 + seq) for seq in range(4)]
    _openclaw_store(tmp_path, "main", {"s1": events}, generations={"s1": "generation-1"})
    source = OpenClawTranscriptSource(tmp_path)

    prepared, out_dir, pending = _prepare_openclaw(
        source,
        tmp_path,
        {
            "main/sessions/s1.jsonl": {
                "container": "sqlite",
                "generation": "generation-1",
                "lines": 3,
                "last_timestamp": None,
            }
        },
    )

    assert prepared == 1
    assert "turn-3" in (out_dir / "1.jsonl").read_text(encoding="utf-8")
    assert "turn-2" not in (out_dir / "1.jsonl").read_text(encoding="utf-8")
    assert pending["main/sessions/s1.jsonl"]["generation"] == "generation-1"
    assert pending["main/sessions/s1.jsonl"]["lines"] == 4


def test_openclaw_generation_rotation_reoffers_rewritten_transcript(tmp_path: pathlib.Path) -> None:
    events = [(seq, _openclaw_turn("user", f"rewritten-{seq}"), 1785308110945 + seq) for seq in range(5)]
    _openclaw_store(tmp_path, "main", {"s1": events}, generations={"s1": "generation-2"})
    source = OpenClawTranscriptSource(tmp_path)

    prepared, out_dir, pending = _prepare_openclaw(
        source,
        tmp_path,
        {
            "main/sessions/s1.jsonl": {
                "container": "sqlite",
                "generation": "generation-1",
                "lines": 10,
                "last_timestamp": None,
            }
        },
    )

    assert prepared == 1
    transcript = (out_dir / "1.jsonl").read_text(encoding="utf-8")
    assert "rewritten-0" in transcript
    assert "rewritten-4" in transcript
    assert pending["main/sessions/s1.jsonl"] == {
        "container": "sqlite",
        "generation": "generation-2",
        "lines": 5,
        "last_timestamp": None,
    }


def test_openclaw_legacy_cursor_migration_reoffers_current_generation(tmp_path: pathlib.Path) -> None:
    """The legacy cursor has no generation or prefix identity, so a container
    switch cannot prove the imported prefix survived a rewrite. Replay once."""
    events = [(seq, _openclaw_turn("user", f"turn-{seq}"), 1785308110945 + seq) for seq in range(4)]
    _openclaw_store(tmp_path, "main", {"s1": events}, generations={"s1": "generation-1"})
    source = OpenClawTranscriptSource(tmp_path)

    prepared, out_dir, pending = _prepare_openclaw(
        source,
        tmp_path,
        {"main/sessions/s1.jsonl": {"lines": 3, "last_timestamp": None}},
    )

    assert prepared == 1
    transcript = (out_dir / "1.jsonl").read_text(encoding="utf-8")
    assert "turn-0" in transcript
    assert "turn-3" in transcript
    assert pending["main/sessions/s1.jsonl"]["generation"] == "generation-1"


def test_openclaw_same_generation_without_new_rows_creates_no_job(tmp_path: pathlib.Path) -> None:
    events = [(seq, _openclaw_turn("user", f"turn-{seq}"), 1785308110945 + seq) for seq in range(3)]
    _openclaw_store(tmp_path, "main", {"s1": events}, generations={"s1": "generation-1"})
    source = OpenClawTranscriptSource(tmp_path)

    prepared, out_dir, pending = _prepare_openclaw(
        source,
        tmp_path,
        {
            "main/sessions/s1.jsonl": {
                "container": "sqlite",
                "generation": "generation-1",
                "lines": 3,
                "last_timestamp": None,
            }
        },
    )

    assert prepared == 0
    assert list(out_dir.glob("*.jsonl")) == []
    assert pending["main/sessions/s1.jsonl"] == {
        "container": "sqlite",
        "generation": "generation-1",
        "lines": 3,
        "last_timestamp": None,
    }


def test_openclaw_rewrite_activity_controls_mixed_store_order(tmp_path: pathlib.Path) -> None:
    """Replacement preserves old event timestamps but advances transcript activity,
    which must lift the rewritten session above the early-stop frontier."""
    _openclaw_store(
        tmp_path,
        "main",
        {
            "rewritten": [(0, _openclaw_turn("user", "old-created-at"), 1_000_000_000_000)],
            "ordinary": [(0, _openclaw_turn("user", "ordinary"), 1_700_000_000_000)],
        },
        activity={"rewritten": 1_800_000_000_000, "ordinary": 1_700_000_000_000},
    )

    source = OpenClawTranscriptSource(tmp_path)
    assert [source.key(path) for path in source.discover()] == [
        "main/sessions/rewritten.jsonl",
        "main/sessions/ordinary.jsonl",
    ]


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


def test_hermes_default_db_follows_hermes_home(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    home = tmp_path / "Hermes Home %41 #片段"
    monkeypatch.setenv("HERMES_HOME", str(home))

    assert state_db_path() == home / "state.db"
    assert HermesTranscriptSource().root() == home


def test_hermes_native_windows_default_uses_local_appdata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("memu.hosts.hermes.sessions.sys.platform", "win32")

    assert state_db_path() == tmp_path / "hermes" / "state.db"


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


def test_hermes_opens_paths_with_uri_special_characters(tmp_path: pathlib.Path) -> None:
    """Pasted raw into a file: URI, '%' would percent-decode and '#' would
    truncate the path — silently taking ?mode=ro with it. So the URI is escaped."""
    import pytest

    weird = tmp_path / "pct %41 #frag"
    weird.mkdir()
    source = HermesTranscriptSource(_hermes_db(weird))

    assert [source.key(path) for path in source.discover()] == ["new", "old"]
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        source._connect().execute("INSERT INTO messages (session_id, role, timestamp) VALUES ('x', 'user', 1)")


# ── WorkBuddy ────────────────────────────────────────────────────────────────


def test_workbuddy_classify_conversation_turns() -> None:
    source = WorkBuddyTranscriptSource()
    user = {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "fix the bug"}],
    }
    assistant = {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "On it."}],
    }
    assert source.classify(_line(user)) is RecordKind.MESSAGE
    assert source.classify(_line(assistant)) is RecordKind.MESSAGE


def test_workbuddy_classify_tool_records() -> None:
    """WorkBuddy logs tool calls and results as standalone records — the same
    pattern Codex uses, unlike Claude Code / Cursor which nest them in message
    content blocks."""
    source = WorkBuddyTranscriptSource()
    function_call = {
        "type": "function_call",
        "name": "Bash",
        "callId": "chatcmpl-tool-abc123",
        "arguments": '{"command": "ls"}',
    }
    function_call_result = {
        "type": "function_call_result",
        "name": "Bash",
        "callId": "chatcmpl-tool-abc123",
        "status": "completed",
        "output": {"type": "text", "text": "file1.txt\nfile2.txt"},
    }
    assert source.classify(_line(function_call)) is RecordKind.TOOL
    assert source.classify(_line(function_call_result)) is RecordKind.TOOL


def test_workbuddy_drops_noise() -> None:
    source = WorkBuddyTranscriptSource()
    reasoning = {
        "type": "reasoning",
        "rawContent": [{"type": "reasoning_text", "text": "thinking..."}],
    }
    snapshot = {"type": "file-history-snapshot", "snapshot": {}}
    title = {"type": "ai-title", "aiTitle": "test session"}
    assert source.classify(_line(reasoning)) is RecordKind.OTHER
    assert source.classify(_line(snapshot)) is RecordKind.OTHER
    assert source.classify(_line(title)) is RecordKind.OTHER
    assert source.classify("not json") is RecordKind.OTHER


def test_workbuddy_timestamp_accepts_epoch_millis() -> None:
    source = WorkBuddyTranscriptSource()
    millis = {"type": "message", "role": "user", "timestamp": 1784435392565}
    iso = {"type": "message", "role": "user", "timestamp": "2026-07-19T04:29:52.565000+00:00"}
    assert source.timestamp(_line(millis)) == "2026-07-19T04:29:52.565000+00:00"
    assert source.timestamp(_line(iso)) == "2026-07-19T04:29:52.565000+00:00"
    assert source.timestamp(_line({"type": "reasoning"})) is None


def test_workbuddy_discover(tmp_path: pathlib.Path) -> None:
    """WorkBuddy keeps one directory per escaped cwd, one JSONL per session."""
    project = tmp_path / "d-Users-proj"
    project.mkdir()
    session = project / "abc-123.jsonl"
    session.write_text(
        '{"type":"message","role":"user","content":[{"type":"input_text","text":"hi"}]}\n',
        encoding="utf-8",
    )
    stray = tmp_path / "app" / "sessions.json"
    stray.parent.mkdir()
    stray.write_text("{}\n", encoding="utf-8")

    source = WorkBuddyTranscriptSource(tmp_path)
    assert source.exists()
    assert source.discover() == [session]
    assert source.key(session) == "d-Users-proj/abc-123.jsonl"
