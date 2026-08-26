from __future__ import annotations

from typing import Annotated, Literal, Self, TypeAlias

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator


class InputModel(BaseModel):
    """Strict base for the versioned developer-input contract."""

    model_config = ConfigDict(extra="forbid")


class BaseItem(InputModel):
    """Fields shared by every ordered conversation item."""

    id: str | None = Field(default=None, min_length=1)
    created_at: AwareDatetime | None = None


class MessageInput(BaseItem):
    """A user or assistant message considered by memory and skill evolution."""

    type: Literal["message"] = "message"
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ToolCallInput(BaseItem):
    """Optional tool activity considered only by skill evolution."""

    type: Literal["tool_call"] = "tool_call"
    name: str = Field(min_length=1)
    arguments: JsonValue = Field(default_factory=dict)


class ToolResultInput(BaseItem):
    """An optional result from a tool call, considered only by skill evolution."""

    type: Literal["tool_result"] = "tool_result"
    content: JsonValue
    tool_call_id: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    is_error: bool | None = None


ConversationItem: TypeAlias = Annotated[
    MessageInput | ToolCallInput | ToolResultInput,
    Field(discriminator="type"),
]


class ConversationInput(InputModel):
    """One ordered conversation submitted for memory and skill evolution."""

    id: str = Field(min_length=1)
    items: list[ConversationItem] = Field(min_length=1)

    @model_validator(mode="after")
    def require_message(self) -> Self:
        if not any(isinstance(item, MessageInput) for item in self.items):
            msg = "conversation must contain at least one message"
            raise ValueError(msg)
        return self


class MemorizeInput(InputModel):
    """A versioned batch of developer-supplied conversations."""

    schema_version: Literal["1.0"] = "1.0"
    batch_id: str = Field(min_length=1)
    conversations: list[ConversationInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_conversation_ids(self) -> Self:
        ids = [conversation.id for conversation in self.conversations]
        if len(ids) != len(set(ids)):
            msg = "conversation ids must be unique within a batch"
            raise ValueError(msg)
        return self


MemoryInputItem: TypeAlias = MessageInput
SkillInputItem: TypeAlias = MessageInput | ToolCallInput | ToolResultInput


def project_memory(conversation: ConversationInput) -> list[MemoryInputItem]:
    """Return the user and assistant messages used for memory evolution."""

    return [item for item in conversation.items if isinstance(item, MessageInput)]


def project_skill(conversation: ConversationInput) -> list[SkillInputItem]:
    """Return all ordered items used for skill evolution."""

    return list(conversation.items)


__all__ = [
    "ConversationInput",
    "ConversationItem",
    "MemorizeInput",
    "MessageInput",
    "ToolCallInput",
    "ToolResultInput",
    "project_memory",
    "project_skill",
]
