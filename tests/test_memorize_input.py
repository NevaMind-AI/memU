from __future__ import annotations

import pytest
from pydantic import ValidationError

from memu.app.memorize.input import (
    MemorizeInput,
    MessageInput,
    ToolCallInput,
    ToolResultInput,
    project_memory,
    project_skill,
)


def _message_payload(**overrides: object) -> dict[str, object]:
    return {"type": "message", "role": "user", "content": "Remember this", **overrides}


def test_minimal_message_only_input_uses_version_1_0() -> None:
    memorize_input = MemorizeInput.model_validate({"items": [_message_payload()]})

    assert memorize_input.schema_version == "1.0"
    assert memorize_input.items == [MessageInput(role="user", content="Remember this")]


def test_memorize_input_parses_ordered_messages_and_optional_tool_activity() -> None:
    memorize_input = MemorizeInput.model_validate({
        "items": [
            _message_payload(role="user", content="Save the config"),
            _message_payload(role="assistant", content="I will write it."),
            {"type": "tool_call", "name": "write_file", "arguments": {"path": "profile.json"}},
            {
                "type": "tool_result",
                "name": "write_file",
                "content": "ok",
                "is_error": False,
            },
        ],
    })

    assert [type(item) for item in memorize_input.items] == [
        MessageInput,
        MessageInput,
        ToolCallInput,
        ToolResultInput,
    ]
    assert [item.type for item in memorize_input.items] == ["message", "message", "tool_call", "tool_result"]


def test_projections_separate_memory_from_skill_without_mutating_input() -> None:
    memorize_input = MemorizeInput(
        items=[
            MessageInput(role="user", content="Save the config"),
            ToolCallInput(name="write_file", arguments={"path": "profile.json"}),
            ToolResultInput(name="write_file", content="ok"),
            MessageInput(role="assistant", content="Saved."),
        ],
    )
    original = memorize_input.model_dump()

    memory = project_memory(memorize_input)
    skill = project_skill(memorize_input)

    assert [item.content for item in memory] == ["Save the config", "Saved."]
    assert [item.type for item in skill] == ["message", "tool_call", "tool_result", "message"]
    assert skill is not memorize_input.items
    assert memorize_input.model_dump() == original


@pytest.mark.parametrize(
    "item",
    [
        _message_payload(id="message-1"),
        _message_payload(created_at="2026-08-26T07:30:00Z"),
        {"type": "tool_call", "id": "call-1", "name": "write_file"},
        {"type": "tool_result", "tool_call_id": "call-1", "content": "ok"},
    ],
)
def test_items_reject_identity_and_timestamp_metadata(item: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        MemorizeInput.model_validate({"items": [_message_payload(), item]})


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"items": []}, "at least 1 item"),
        (
            {"items": [{"type": "tool_call", "name": "search"}]},
            "at least one message",
        ),
        (
            {"items": [_message_payload(role="system")]},
            "user.*assistant",
        ),
        (
            {"items": [{"type": "attachment", "content": "x"}]},
            "union_tag_invalid",
        ),
        (
            {"items": [_message_payload(extra="unexpected")]},
            "extra_forbidden",
        ),
        (
            {"items": [_message_payload()], "batch_id": "batch-1"},
            "extra_forbidden",
        ),
        (
            {"items": [_message_payload()], "conversations": []},
            "extra_forbidden",
        ),
    ],
)
def test_memorize_input_rejects_invalid_shapes(payload: dict[str, object], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        MemorizeInput.model_validate(payload)


def test_memorize_input_json_round_trip_and_schema() -> None:
    memorize_input = MemorizeInput(items=[MessageInput(role="user", content="Hello")])

    restored = MemorizeInput.model_validate_json(memorize_input.model_dump_json())
    schema = MemorizeInput.model_json_schema()

    assert restored == memorize_input
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["items"]["minItems"] == 1
    assert "batch_id" not in schema["properties"]
    assert "conversations" not in schema["properties"]
