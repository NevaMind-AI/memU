from __future__ import annotations

from typing import Annotated, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class InputModel(BaseModel):
    """Strict base for the versioned developer-input contract."""

    model_config = ConfigDict(extra="forbid")


class MessageInput(InputModel):
    """A user or assistant message considered by memory and skill evolution."""

    type: Literal["message"] = "message"
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ToolCallInput(InputModel):
    """Optional tool activity considered only by skill evolution."""

    type: Literal["tool_call"] = "tool_call"
    name: str = Field(min_length=1)
    arguments: JsonValue = Field(default_factory=dict)


class ToolResultInput(InputModel):
    """An optional result from a tool call, considered only by skill evolution."""

    type: Literal["tool_result"] = "tool_result"
    content: JsonValue
    name: str | None = Field(default=None, min_length=1)
    is_error: bool | None = None


ConversationItem: TypeAlias = Annotated[
    MessageInput | ToolCallInput | ToolResultInput,
    Field(discriminator="type"),
]


class MemorizeInput(InputModel):
    """One ordered developer-supplied session for memory and skill evolution."""

    schema_version: Literal["1.0"] = "1.0"
    items: list[ConversationItem] = Field(min_length=1)

    @model_validator(mode="after")
    def require_message(self) -> Self:
        if not any(isinstance(item, MessageInput) for item in self.items):
            msg = "memorize input must contain at least one message"
            raise ValueError(msg)
        return self


MemoryInputItem: TypeAlias = MessageInput
SkillInputItem: TypeAlias = MessageInput | ToolCallInput | ToolResultInput


def project_memory(memorize_input: MemorizeInput) -> list[MemoryInputItem]:
    """Return the user and assistant messages used for memory evolution."""

    return [item for item in memorize_input.items if isinstance(item, MessageInput)]


def project_skill(memorize_input: MemorizeInput) -> list[SkillInputItem]:
    """Return all ordered items used for skill evolution."""

    return list(memorize_input.items)


__all__ = [
    "ConversationItem",
    "MemorizeInput",
    "MessageInput",
    "ToolCallInput",
    "ToolResultInput",
    "project_memory",
    "project_skill",
]
