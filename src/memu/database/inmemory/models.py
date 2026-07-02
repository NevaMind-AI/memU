from __future__ import annotations

from pydantic import BaseModel

from memu.database.models import (
    RecallEntry,
    RecallFile,
    RecallFileEntry,
    RecallFileResource,
    RecallFileSegment,
    Resource,
    merge_scope_model,
)


class InMemoryResource(Resource):
    """Concrete in-memory resource model."""


class InMemoryRecallEntry(RecallEntry):
    """Concrete in-memory memory item model."""


class InMemoryRecallFile(RecallFile):
    """Concrete in-memory memory category model."""


class InMemoryFileEntry(RecallFileEntry):
    """Concrete in-memory relation model."""


class InMemoryFileResource(RecallFileResource):
    """Concrete in-memory resource-category relation model."""


class InMemoryFileSegment(RecallFileSegment):
    """Concrete in-memory file-segment model."""


def build_inmemory_models(
    user_model: type[BaseModel],
) -> tuple[
    type[InMemoryResource],
    type[InMemoryRecallFile],
    type[InMemoryRecallEntry],
    type[InMemoryFileEntry],
    type[InMemoryFileResource],
    type[InMemoryFileSegment],
]:
    """
    Build scoped in-memory models that inherit from both the base interface and the user scope model.
    """
    resource_model = merge_scope_model(user_model, InMemoryResource, name_suffix="Resource")
    recall_file_model = merge_scope_model(user_model, InMemoryRecallFile, name_suffix="RecallFile")
    recall_entry_model = merge_scope_model(user_model, InMemoryRecallEntry, name_suffix="RecallEntry")
    recall_file_entry_model = merge_scope_model(user_model, InMemoryFileEntry, name_suffix="RecallFileEntry")
    recall_file_resource_model = merge_scope_model(user_model, InMemoryFileResource, name_suffix="RecallFileResource")
    recall_file_segment_model = merge_scope_model(user_model, InMemoryFileSegment, name_suffix="RecallFileSegment")
    return (
        resource_model,
        recall_file_model,
        recall_entry_model,
        recall_file_entry_model,
        recall_file_resource_model,
        recall_file_segment_model,
    )


__all__ = [
    "InMemoryFileEntry",
    "InMemoryFileResource",
    "InMemoryFileSegment",
    "InMemoryRecallEntry",
    "InMemoryRecallFile",
    "InMemoryResource",
    "build_inmemory_models",
]
