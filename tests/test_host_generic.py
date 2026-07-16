"""The generic adapter: does the dialect sniffer read every known shape, and does
detect() draw the right memorization/retrieval verdicts from a directory?"""

from __future__ import annotations

import json
import pathlib

from memu.hosts.base import RecordKind
from memu.hosts.generic.detect import probe, render, scan_home
from memu.hosts.generic.sessions import GenericTranscriptSource


def _line(entry: dict) -> str:
    return json.dumps(entry)


SOURCE = GenericTranscriptSource("~")


# ── the sniffer, one case per dialect ─────────────────────────────────────────


def test_sniffs_payload_wrapped_codex_shape() -> None:
    assert SOURCE.classify(_line({"payload": {"type": "message", "role": "user"}})) is RecordKind.MESSAGE
    assert SOURCE.classify(_line({"payload": {"type": "function_call", "name": "shell"}})) is RecordKind.TOOL
    assert SOURCE.classify(_line({"payload": {"type": "reasoning"}})) is RecordKind.OTHER


def test_sniffs_typed_message_tree_openclaw_shape() -> None:
    user = {"type": "message", "message": {"role": "user", "content": "hi"}}
    tool = {"type": "message", "message": {"role": "toolResult", "content": []}}
    assert SOURCE.classify(_line(user)) is RecordKind.MESSAGE
    assert SOURCE.classify(_line(tool)) is RecordKind.TOOL
    assert SOURCE.classify(_line({"type": "compaction"})) is RecordKind.OTHER


def test_sniffs_typed_block_claude_shape() -> None:
    text = {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hey"}]}}
    tool_result = {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}}
    thinking = {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "thinking"}]}}
    meta = {"type": "user", "isMeta": True, "message": {"role": "user", "content": "<injected>"}}
    assert SOURCE.classify(_line(text)) is RecordKind.MESSAGE
    assert SOURCE.classify(_line(tool_result)) is RecordKind.TOOL
    assert SOURCE.classify(_line(thinking)) is RecordKind.OTHER
    assert SOURCE.classify(_line(meta)) is RecordKind.OTHER


def test_sniffs_role_message_cursor_shape() -> None:
    user = {"role": "user", "message": {"content": [{"type": "text", "text": "hi"}]}}
    tool = {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": "Shell"}]}}
    assert SOURCE.classify(_line(user)) is RecordKind.MESSAGE
    assert SOURCE.classify(_line(tool)) is RecordKind.TOOL


def test_sniffs_flat_openai_chat_rows() -> None:
    assert SOURCE.classify(_line({"role": "user", "content": "do the thing"})) is RecordKind.MESSAGE
    assert SOURCE.classify(_line({"role": "assistant", "tool_calls": [{"id": "1"}]})) is RecordKind.TOOL
    assert SOURCE.classify(_line({"role": "tool", "content": "ok", "tool_call_id": "1"})) is RecordKind.TOOL
    assert SOURCE.classify(_line({"role": "system", "content": "you are"})) is RecordKind.OTHER
    assert SOURCE.classify("not json") is RecordKind.OTHER


def test_timestamp_handles_iso_epoch_and_payload() -> None:
    assert SOURCE.timestamp(_line({"timestamp": "2026-07-16T00:00:00Z"})) == "2026-07-16T00:00:00Z"
    assert SOURCE.timestamp(_line({"timestamp": 1752537600000})) == "2025-07-15T00:00:00+00:00"
    assert SOURCE.timestamp(_line({"payload": {"timestamp": "2026-07-16T00:00:00Z"}})) == "2026-07-16T00:00:00Z"
    assert SOURCE.timestamp(_line({"role": "user"})) is None


# ── detect: the two verdicts ──────────────────────────────────────────────────


def _agent_dir(tmp_path: pathlib.Path, *, sessions: bool, instructions: bool) -> pathlib.Path:
    root = tmp_path / ".someagent"
    root.mkdir()
    if sessions:
        log = root / "sessions" / "abc.jsonl"
        log.parent.mkdir()
        log.write_text(
            _line({"role": "user", "content": "hello"}) + "\n" + _line({"role": "assistant", "content": "hi"}) + "\n",
            encoding="utf-8",
        )
    if instructions:
        (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    return root


def test_detect_reports_memorization_when_sessions_sniff(tmp_path: pathlib.Path) -> None:
    result = probe(_agent_dir(tmp_path, sessions=True, instructions=False))
    assert result.memorization
    assert not result.retrieval
    text = render(result)
    assert "memorization: works" in text
    assert "retrieval: no instruction file found" in text


def test_detect_falls_back_to_retrieval_when_no_sessions(tmp_path: pathlib.Path) -> None:
    result = probe(_agent_dir(tmp_path, sessions=False, instructions=True))
    assert not result.memorization
    assert result.retrieval
    text = render(result)
    assert "memorization: no — no session log found" in text
    assert "retrieval: works" in text and "AGENTS.md" in text


def test_detect_flags_unrecognized_jsonl_and_sqlite(tmp_path: pathlib.Path) -> None:
    root = tmp_path / ".weird"
    root.mkdir()
    (root / "metrics.jsonl").write_text('{"event":"boot","ms":12}\n', encoding="utf-8")
    (root / "state.db").write_text("not really sqlite", encoding="utf-8")

    result = probe(root)
    assert not result.memorization and result.session_files
    text = render(result)
    assert "no record matched a known dialect" in text


def test_detect_points_dedicated_hosts_at_their_binary(tmp_path: pathlib.Path) -> None:
    root = tmp_path / ".codex"
    root.mkdir()
    (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    assert "memu-codex" in render(probe(root))


def test_scan_home_finds_only_plausible_agents(tmp_path: pathlib.Path) -> None:
    _agent_dir(tmp_path, sessions=True, instructions=True)
    (tmp_path / ".empty").mkdir()
    (tmp_path / ".dotfile").write_text("not a dir", encoding="utf-8")

    results = scan_home(tmp_path)
    assert [result.path.name for result in results] == [".someagent"]
    assert results[0].memorization and results[0].retrieval


def test_generic_prepare_requires_session_dir() -> None:
    import pytest

    from memu.hosts.generic.cli import SPEC
    from memu.hosts.host_cli import build_parser

    parser = build_parser(SPEC)
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["prepare"])
    assert excinfo.value.code == 2
