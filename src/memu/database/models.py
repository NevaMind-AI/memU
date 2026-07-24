from __future__ import annotations

import uuid
from datetime import datetime

import pendulum
from pydantic import BaseModel, ConfigDict, Field


class BaseRecord(BaseModel):
    """Backend-agnostic record interface."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    updated_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))


class Resource(BaseRecord):
    url: str
    local_path: str
    caption: str | None = None
    embedding: list[float] | None = None
    # Which workspace track this resource came from. ``commit_results`` writes
    # "workspace", which is the track ``progressive_retrieve`` surfaces.
    track: str | None = None


class RecallFile(BaseRecord):
    name: str
    # Which track this file belongs to: "memory" (a memory file) or "skill"
    # (a synthesized skill). Defaults to "memory" so existing rows backfill correctly.
    track: str = "memory"
    description: str
    embedding: list[float] | None = None
    content: str | None = None


class RecallFileSegment(BaseRecord):
    """A searchable slice (L2 item) of a ``RecallFile`` (ADR 0007).

    Each file has 1..n segments; ``text`` is the embed/search unit and ``embedding``
    its vector. Retrieval ranks segments and rolls the top hits up to their file via
    ``recall_file_id``. Segments carry no ordinal: how a file is sliced is track-specific
    and not necessarily sequential, so position would not be informative.

    ``track`` mirrors the owning file's track ("memory"/"skill"), denormalized here so
    retrieval can filter segments by track with a plain column predicate instead of a
    join. It is immutable for a segment's lifetime (segments are drop-and-recreated when
    a file is re-sliced), so it never drifts from the file.
    """

    recall_file_id: str
    track: str = "memory"
    text: str
    embedding: list[float] | None = None


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
) -> tuple[
    type[Resource],
    type[RecallFile],
    type[RecallFileSegment],
]:
    """
    Build scoped interface models (Pydantic) that inherit from the base record models and user scope.
    """
    resource_model = merge_scope_model(user_model, Resource, name_suffix="Resource")
    recall_file_model = merge_scope_model(user_model, RecallFile, name_suffix="RecallFile")
    recall_file_segment_model = merge_scope_model(user_model, RecallFileSegment, name_suffix="RecallFileSegment")
    return (
        resource_model,
        recall_file_model,
        recall_file_segment_model,
    )


__all__ = [
    "BaseRecord",
    "RecallFile",
    "RecallFileSegment",
    "Resource",
    "build_scoped_models",
    "merge_scope_model",
]
