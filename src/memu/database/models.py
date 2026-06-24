from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from os.path import basename
from typing import Any, Literal

import pendulum
from pydantic import BaseModel, ConfigDict, Field

# Sub-type of a memory-lane entry (kept for prompt routing / backward semantics).
MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill", "tool"]

# A lane is one of the parallel, structurally identical processing tracks that
# share the same Resource -> canonical-text trunk:
#   - "source": raw input artifacts (conversation/document/image/video/audio)
#   - "index":  per-resource catalog/description docs
#   - "memory": grouped memory docs (the former "category")
#   - "skill":  grouped reusable-skill docs
# index/memory/skill are the three retrievable lanes; "source" holds raw inputs.
Lane = Literal["source", "index", "memory", "skill"]
SOURCE_LANE: Lane = "source"
RETRIEVAL_LANES: tuple[Lane, ...] = ("index", "memory", "skill")
MARKDOWN_MODALITY = "markdown"


def compute_content_hash(text: str, entry_kind: str) -> str:
    """Generate a stable hash for entry deduplication.

    Operates on post-extraction content. Normalizes whitespace to absorb minor
    formatting differences ("I love coffee" vs "I  love  coffee").
    """
    normalized = " ".join(text.lower().split())
    content = f"{entry_kind}:{normalized}"
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
    """A node in the unified store: either a raw input or a generated lane doc.

    "Everything is a resource":
      - raw inputs:      ``lane="source"``, ``modality`` = conversation/document/
                         image/video/audio; ``content`` holds the canonical,
                         modality-agnostic text from preprocessing (the trunk).
      - generated docs:  ``lane`` in {index, memory, skill}, ``modality="markdown"``,
                         rendered as ``resource/<lane>/<slug>.md``; ``content`` holds
                         the markdown body, ``summary`` the searchable condensation.
    """

    lane: str = SOURCE_LANE
    modality: str
    url: str | None = None
    local_path: str | None = None
    # Filename stem used for ``resource/<lane>/<slug>.md`` (generated docs only).
    slug: str | None = None
    # Human title of a generated doc (the former category/skill name).
    title: str | None = None
    # Short blurb for a generated doc (the former category description).
    description: str | None = None
    # Raw: canonical text from preprocessing. Doc: rendered markdown body.
    content: str | None = None
    # Searchable condensation used for coarse (resource-level) recall.
    summary: str | None = None
    embedding: list[float] | None = None
    # Provenance: raw sources a generated doc derives from. Each dict holds at
    # least ``resource_id`` and ``source_path`` (plus optional ``modality``).
    resource_refs: list[dict[str, Any]] = []

    @property
    def source_path(self) -> str:
        """Path relative to the ``resource/`` root for this artifact."""
        if self.lane != SOURCE_LANE and self.slug:
            return f"resource/{self.lane}/{self.slug}.md"
        name = basename(self.local_path or self.url or self.id)
        return f"resource/{name}"


class Entry(BaseRecord):
    """The searchable atom of a lane (index description / memory item / skill step)."""

    lane: str
    # Originating raw source resource (provenance), and its relative path.
    source_id: str | None = None
    source_path: str | None = None
    # Sub-type within a lane (memory: profile/event/...; skill: step kind; etc.).
    entry_kind: str
    text: str
    embedding: list[float] | None = None
    happened_at: datetime | None = None
    extra: dict[str, Any] = {}
    # extra may contain:
    # - content_hash / reinforcement_count / last_reinforced_at (salience)
    # - ref_id (reference tracking)
    # - when_to_use / metadata / tool_calls (tool memory)


class ResourceEntry(BaseRecord):
    """Edge: membership of an Entry in its coarse (lane) Resource doc."""

    entry_id: str
    resource_id: str


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
) -> tuple[type[Resource], type[Entry], type[ResourceEntry]]:
    """Build scoped interface models that inherit base records and the user scope."""
    resource_model = merge_scope_model(user_model, Resource, name_suffix="Resource")
    entry_model = merge_scope_model(user_model, Entry, name_suffix="Entry")
    resource_entry_model = merge_scope_model(user_model, ResourceEntry, name_suffix="ResourceEntry")
    return resource_model, entry_model, resource_entry_model


__all__ = [
    "MARKDOWN_MODALITY",
    "RETRIEVAL_LANES",
    "SOURCE_LANE",
    "BaseRecord",
    "Entry",
    "Lane",
    "MemoryType",
    "Resource",
    "ResourceEntry",
    "ToolCallResult",
    "build_scoped_models",
    "compute_content_hash",
    "merge_scope_model",
]
