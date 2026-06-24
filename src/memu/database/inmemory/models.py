from __future__ import annotations

from pydantic import BaseModel

from memu.database.models import (
    Entry,
    Resource,
    ResourceEntry,
    merge_scope_model,
)


class InMemoryResource(Resource):
    """Concrete in-memory resource model."""


class InMemoryEntry(Entry):
    """Concrete in-memory entry model."""


class InMemoryResourceEntry(ResourceEntry):
    """Concrete in-memory membership-edge model."""


def build_inmemory_models(
    user_model: type[BaseModel],
) -> tuple[
    type[InMemoryResource],
    type[InMemoryEntry],
    type[InMemoryResourceEntry],
]:
    """Build scoped in-memory models inheriting both base interface and user scope."""
    resource_model = merge_scope_model(user_model, InMemoryResource, name_suffix="Resource")
    entry_model = merge_scope_model(user_model, InMemoryEntry, name_suffix="Entry")
    resource_entry_model = merge_scope_model(user_model, InMemoryResourceEntry, name_suffix="ResourceEntry")
    return resource_model, entry_model, resource_entry_model


__all__ = [
    "InMemoryEntry",
    "InMemoryResource",
    "InMemoryResourceEntry",
    "build_inmemory_models",
]
