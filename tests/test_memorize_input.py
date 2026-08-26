from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from memu.app import (
    ConversationInput,
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
    memorize_input = MemorizeInput.model_validate({
        "batch_id": "batch-1",
        "conversations": [{"id": "chat-1", "items": [_message_payload()]}],
    })

    assert memorize_input.schema_version == "1.0"
    assert memorize_input.batch_id == "batch-1"
    assert memorize_input.conversations[0].items == [
        MessageInput(role="user", content="Remember this"),
    ]


def test_conversation_parses_ordered_messages_and_optional_tool_activity() -> None:
    conversation = ConversationInput.model_validate({
        "id": "chat-1",
        "items": [
            _message_payload(role="user", content="Save the config"),
            _message_payload(role="assistant", content="I will write it."),
            {"type": "tool_call", "name": "write_file", "arguments": {"path": "profile.json"}},
            {
                "type": "tool_result",
                "tool_call_id": "call-1",
                "name": "write_file",
                "content": "ok",
                "is_error": False,
            },
        ],
    })

    assert [type(item) for item in conversation.items] == [
        MessageInput,
        MessageInput,
        ToolCallInput,
        ToolResultInput,
    ]
    assert [item.type for item in conversation.items] == ["message", "message", "tool_call", "tool_result"]


def test_projections_separate_memory_from_skill_without_mutating_input() -> None:
    conversation = ConversationInput(
        id="chat-1",
        items=[
            MessageInput(role="user", content="Save the config"),
            ToolCallInput(name="write_file", arguments={"path": "profile.json"}),
            ToolResultInput(name="write_file", content="ok"),
            MessageInput(role="assistant", content="Saved."),
        ],
    )
    original = conversation.model_dump()

    memory = project_memory(conversation)
    skill = project_skill(conversation)

    assert [item.content for item in memory] == ["Save the config", "Saved."]
    assert [item.type for item in skill] == ["message", "tool_call", "tool_result", "message"]
    assert skill is not conversation.items
    assert conversation.model_dump() == original


def test_optional_item_identity_and_aware_timestamp_round_trip() -> None:
    created_at = datetime(2026, 8, 26, 7, 30, tzinfo=UTC)
    item = MessageInput(id="message-1", created_at=created_at, role="assistant", content="Done")

    restored = MessageInput.model_validate_json(item.model_dump_json())

    assert restored == item
    assert restored.created_at == created_at


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"id": "chat-1", "items": []}, "at least 1 item"),
        (
            {"id": "chat-1", "items": [{"type": "tool_call", "name": "search"}]},
            "at least one message",
        ),
        (
            {"id": "chat-1", "items": [_message_payload(role="system")]},
            "user.*assistant",
        ),
        (
            {"id": "chat-1", "items": [{"type": "attachment", "content": "x"}]},
            "union_tag_invalid",
        ),
        (
            {"id": "chat-1", "items": [_message_payload(extra="unexpected")]},
            "extra_forbidden",
        ),
    ],
)
def test_conversation_rejects_invalid_shapes(payload: dict[str, object], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        ConversationInput.model_validate(payload)


def test_memorize_input_rejects_duplicate_conversation_ids() -> None:
    conversation = {"id": "chat-1", "items": [_message_payload()]}

    with pytest.raises(ValidationError, match="conversation ids must be unique"):
        MemorizeInput.model_validate({
            "batch_id": "batch-1",
            "conversations": [conversation, conversation],
        })


def test_memorize_input_json_round_trip_and_schema() -> None:
    memorize_input = MemorizeInput(
        batch_id="batch-1",
        conversations=[ConversationInput(id="chat-1", items=[MessageInput(role="user", content="Hello")])],
    )

    restored = MemorizeInput.model_validate_json(memorize_input.model_dump_json())
    schema = MemorizeInput.model_json_schema()

    assert restored == memorize_input
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["conversations"]["minItems"] == 1
