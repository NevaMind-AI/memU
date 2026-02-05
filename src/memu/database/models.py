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
    # extra may contains:
    # # reinforcement tracking fields
    # - content_hash: str
    # - reinforcement_count: int
    # - last_reinforced_at: str (isoformat)
    # # Reference tracking field
    # - ref_id: str

    when_to_use: str | None = Field(default=None, description="Hint for when this memory should be retrieved")
    metadata: dict[str, Any] | None = Field(default=None, description="Type-specific metadata")
    tool_calls: list[ToolCallResult] | None = Field(default=None, description="Tool call history for tool memories")

    def add_tool_call(self, tool_call: ToolCallResult) -> None:
        """Add a tool call result to this memory (for tool type memories)."""
        if self.memory_type != "tool":
            msg = "add_tool_call can only be used with tool type memories"
            raise ValueError(msg)
        tool_call.ensure_hash()
        if self.tool_calls is None:
            self.tool_calls = []
        self.tool_calls.append(tool_call)

    def get_tool_statistics(self, recent_n: int = 20) -> dict[str, float]:
        """Calculate statistics for the most recent N tool calls.

        Returns:
            Dictionary with avg_time_cost, success_rate, avg_score, avg_token_cost
        """
        if not self.tool_calls:
            return {
                "total_calls": 0,
                "recent_calls_analyzed": 0,
                "avg_time_cost": 0.0,
                "success_rate": 0.0,
                "avg_score": 0.0,
                "avg_token_cost": 0.0,
            }

        recent_calls = self.tool_calls[-recent_n:]
        recent_count = len(recent_calls)

        # Calculate statistics
        total_time = sum(c.time_cost for c in recent_calls)
        avg_time_cost = total_time / recent_count if recent_count > 0 else 0.0

        successful = sum(1 for c in recent_calls if c.success)
        success_rate = successful / recent_count if recent_count > 0 else 0.0

        total_score = sum(c.score for c in recent_calls)
        avg_score = total_score / recent_count if recent_count > 0 else 0.0

        valid_token_calls = [c for c in recent_calls if c.token_cost >= 0]
        avg_token_cost = (
            sum(c.token_cost for c in valid_token_calls) / len(valid_token_calls) if valid_token_calls else 0.0
        )

        return {
            "total_calls": len(self.tool_calls),
            "recent_calls_analyzed": recent_count,
            "avg_time_cost": round(avg_time_cost, 3),
            "success_rate": round(success_rate, 4),
            "avg_score": round(avg_score, 3),
            "avg_token_cost": round(avg_token_cost, 2),
        }


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
