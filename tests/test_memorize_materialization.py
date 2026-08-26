from __future__ import annotations

import json
from pathlib import Path

import pytest

from memu.app.memorize import materialize as materialize_module
from memu.app.memorize.input import MemorizeInput, MessageInput, ToolCallInput, ToolResultInput
from memu.app.memorize.materialize import materialize_memorize_input


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_materializes_one_session_to_fixed_transcript_pair(tmp_path: Path) -> None:
    memorize_input = MemorizeInput(
        items=[
            MessageInput(role="user", content="First"),
            MessageInput(role="assistant", content="Second"),
        ],
    )

    result = materialize_memorize_input(memorize_input, tmp_path)

    assert (result.memory_path.name, result.skill_path.name) == ("1.jsonl", "1_full.jsonl")
    assert [item["content"] for item in _read_jsonl(result.memory_path)] == ["First", "Second"]


def test_memory_excludes_tools_while_skill_preserves_item_order(tmp_path: Path) -> None:
    memorize_input = MemorizeInput(
        items=[
            MessageInput(role="user", content="Write it"),
            ToolCallInput(name="write_file", arguments={"path": "profile.json"}),
            ToolResultInput(name="write_file", content="ok"),
            MessageInput(role="assistant", content="Done"),
        ],
    )

    result = materialize_memorize_input(memorize_input, tmp_path)

    assert [item["type"] for item in _read_jsonl(result.memory_path)] == ["message", "message"]
    assert [item["type"] for item in _read_jsonl(result.skill_path)] == [
        "message",
        "tool_call",
        "tool_result",
        "message",
    ]


def test_message_only_session_produces_equivalent_views(tmp_path: Path) -> None:
    memorize_input = MemorizeInput(
        items=[
            MessageInput(role="user", content="Hello"),
            MessageInput(role="assistant", content="Hi"),
        ],
    )

    result = materialize_memorize_input(memorize_input, tmp_path)

    assert result.memory_path.read_bytes() == result.skill_path.read_bytes()


def test_serializes_unicode_structured_values(tmp_path: Path) -> None:
    memorize_input = MemorizeInput(
        items=[
            MessageInput(role="user", content="记住深烘咖啡"),
            ToolCallInput(name="store", arguments={"nested": [1, True, None, {"中文": "值"}]}),
            ToolResultInput(content=None, is_error=None),
        ],
    )

    result = materialize_memorize_input(memorize_input, tmp_path)
    items = _read_jsonl(result.skill_path)

    assert "记住深烘咖啡" in result.skill_path.read_text(encoding="utf-8")
    assert items[1]["arguments"] == {"nested": [1, True, None, {"中文": "值"}]}
    assert items[2]["content"] is None
    assert "is_error" not in items[2]


def test_replaces_stale_jsonl_and_preserves_other_files(tmp_path: Path) -> None:
    (tmp_path / "1.jsonl").write_text("stale", encoding="utf-8")
    (tmp_path / "8_full.jsonl").write_text("stale", encoding="utf-8")
    marker = tmp_path / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    memorize_input = MemorizeInput(items=[MessageInput(role="user", content="Fresh")])

    materialize_memorize_input(memorize_input, tmp_path)

    assert sorted(path.name for path in tmp_path.glob("*.jsonl")) == ["1.jsonl", "1_full.jsonl"]
    assert _read_jsonl(tmp_path / "1.jsonl")[0]["content"] == "Fresh"
    assert marker.read_text(encoding="utf-8") == "keep"


def test_materialization_does_not_modify_input_and_returns_requested_paths(tmp_path: Path) -> None:
    memorize_input = MemorizeInput(items=[MessageInput(role="user", content="Hello")])
    original = memorize_input.model_dump()

    result = materialize_memorize_input(memorize_input, tmp_path / "nested" / "input")

    assert memorize_input.model_dump() == original
    assert result.memory_path == tmp_path / "nested" / "input" / "1.jsonl"
    assert result.skill_path == tmp_path / "nested" / "input" / "1_full.jsonl"


def test_atomic_write_failure_preserves_existing_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "1.jsonl"
    target.write_text("old\n", encoding="utf-8")

    def fail_replace(source: str, destination: Path) -> None:
        del source, destination
        msg = "replace failed"
        raise OSError(msg)

    monkeypatch.setattr(materialize_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        materialize_module._atomic_write_text(target, "new\n")

    assert target.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob(".tmp-*")) == []
