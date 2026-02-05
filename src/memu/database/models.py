from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Literal

import pendulum
from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill", "tool"]


def compute_content_hash(summary: str, memory_type: str) -> str:
    """
    Generate unique hash for memory deduplication.

    Operates on post-summary content. Normalizes whitespace to handle
    minor formatting differences like "I love coffee" vs "I  love  coffee".

    Args:
        summary: The memory summary text
        memory_type: The type of memory (profile, event, etc.)

    Returns:
        A 16-character hex hash string
    """
    # Normalize: lowercase, strip, collapse whitespace
    normalized = " ".join(summary.lower().split())
    content = f"{memory_type}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class BaseRecord(BaseModel):
    """Backend-agnostic record interface."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    updated_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))


class ToolCallResult(BaseModel):
    """Represents the result of a tool invocation for Tool Memory."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    input: dict[str, Any] | str = Field(default="", description="Tool input parameters")
    output: str = Field(default="", description="Tool output result")
    success: bool = Field(default=True, description="Whether the tool invocation succeeded")
    time_cost: float = Field(default=0.0, description="Time consumed by the tool invocation in seconds")
    token_cost: int = Field(default=-1, description="Token consumption of the tool (-1 if unknown)")
    score: float = Field(default=0.0, description="Quality score from 0.0 to 1.0")
    call_hash: str = Field(default="", description="Hash of input+output for deduplication")
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))

    def generate_hash(self) -> str:
        """Generate MD5 hash from tool input and output for deduplication."""
        input_str = json.dumps(self.input, sort_keys=True) if isinstance(self.input, dict) else str(self.input)
        combined = f"{self.tool_name}|{input_str}|{self.output}"
        return hashlib.md5(combined.encode("utf-8"), usedforsecurity=False).hexdigest()

    def ensure_hash(self) -> None:
        """Ensure call_hash is set, generate if empty."""
        if not self.call_hash:
            self.call_hash = self.generate_hash()


class Resource(BaseRecord):
    url: str
    modality: str
    local_path: str
    caption: str | None = None
    embedding: list[float] | None = None


class MemoryItem(BaseRecord):
    resource_id: str | None
    memory_type: str
    summary: str
    embedding: list[float] | None = None
    happened_at: datetime | None = None
    extra: dict[str, Any] = {}
    # extra may contain:
    # # reinforcement tracking fields
    # - content_hash: str
    # - reinforcement_count: int
    # - last_reinforced_at: str (isoformat)
    # # Reference tracking field
    # - ref_id: str
    # # Tool memory fields
    # - when_to_use: str - Hint for when this memory should be retrieved
    # - metadata: dict - Type-specific metadata (e.g., tool_name, avg_success_rate)
    # - tool_calls: list[dict] - Tool call history for tool memories (serialized ToolCallResult)


class MemoryCategory(BaseRecord):
    name: str
    description: str
    embedding: list[float] | None = None
    summary: str | None = None


class CategoryItem(BaseRecord):
    item_id: str
    category_id: str


def merge_scope_model[TBaseRecord: BaseRecord](
    user_model: type[BaseModel], core_model: type[TBaseRecord], *, name_suffix: str
) -> type[TBaseRecord]:
    """Create a scoped model inheriting both the user scope model and the core model."""
    overlap = set(user_model.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    return type(
        f"{user_model.__name__}{core_model.__name__}{name_suffix}",
        (user_model, core_model),
        {"model_config": ConfigDict(extra="allow")},
    )


def build_scoped_models(
    user_model: type[BaseModel],
) -> tuple[type[Resource], type[MemoryCategory], type[MemoryItem], type[CategoryItem]]:
    """
    Build scoped interface models (Pydantic) that inherit from the base record models and user scope.
    """
    resource_model = merge_scope_model(user_model, Resource, name_suffix="Resource")
    memory_category_model = merge_scope_model(user_model, MemoryCategory, name_suffix="MemoryCategory")
    memory_item_model = merge_scope_model(user_model, MemoryItem, name_suffix="MemoryItem")
    category_item_model = merge_scope_model(user_model, CategoryItem, name_suffix="CategoryItem")
    return resource_model, memory_category_model, memory_item_model, category_item_model


__all__ = [
    "BaseRecord",
    "CategoryItem",
    "MemoryCategory",
    "MemoryItem",
    "MemoryType",
    "Resource",
    "ToolCallResult",
    "build_scoped_models",
    "compute_content_hash",
    "merge_scope_model",
]
