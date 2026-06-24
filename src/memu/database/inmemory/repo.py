from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from memu.database.inmemory.models import build_inmemory_models
from memu.database.inmemory.repositories import (
    InMemoryEntryRepository,
    InMemoryResourceEntryRepository,
    InMemoryResourceRepository,
)
from memu.database.inmemory.state import InMemoryState
from memu.database.interfaces import Database
from memu.database.models import Entry, Resource, ResourceEntry
from memu.database.repositories import EntryRepo, ResourceEntryRepo, ResourceRepo


class InMemoryStore(Database):
    def __init__(
        self,
        *,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        entry_model: type[Any] | None = None,
        resource_entry_model: type[Any] | None = None,
        state: InMemoryState | None = None,
    ) -> None:
        self.scope_model = scope_model or BaseModel
        (
            default_resource_model,
            default_entry_model,
            default_resource_entry_model,
        ) = build_inmemory_models(self.scope_model)

        self.state = state or InMemoryState()
        self.resources: dict[str, Resource] = self.state.resources
        self.entries: dict[str, Entry] = self.state.entries
        self.relations: list[ResourceEntry] = self.state.relations

        resource_model = resource_model or default_resource_model or Resource
        entry_model = entry_model or default_entry_model or Entry
        resource_entry_model = resource_entry_model or default_resource_entry_model or ResourceEntry

        self.resource_repo: ResourceRepo = InMemoryResourceRepository(state=self.state, resource_model=resource_model)
        self.entry_repo: EntryRepo = InMemoryEntryRepository(state=self.state, entry_model=entry_model)
        self.resource_entry_repo: ResourceEntryRepo = InMemoryResourceEntryRepository(
            state=self.state, resource_entry_model=resource_entry_model
        )

    def close(self) -> None:
        return None
