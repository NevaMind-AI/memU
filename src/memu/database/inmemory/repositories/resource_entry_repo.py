from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import ResourceEntry
from memu.database.repositories.resource_entry import ResourceEntryRepo


class InMemoryResourceEntryRepository(ResourceEntryRepo):
    def __init__(self, *, state: InMemoryState, resource_entry_model: type[ResourceEntry]) -> None:
        self._state = state
        self.resource_entry_model = resource_entry_model
        self.relations: list[ResourceEntry] = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        if not where:
            return list(self.relations)
        return [rel for rel in self.relations if matches_where(rel, where)]

    def link_entry_resource(self, entry_id: str, resource_id: str, user_data: dict[str, Any]) -> ResourceEntry:
        for rel in self.relations:
            if rel.entry_id == entry_id and rel.resource_id == resource_id:
                return rel
        rel = self.resource_entry_model(id=str(uuid.uuid4()), entry_id=entry_id, resource_id=resource_id, **user_data)
        self.relations.append(rel)
        return rel

    def load_existing(self) -> None:
        return None

    @override
    def get_entry_resources(self, entry_id: str) -> list[ResourceEntry]:
        return [rel for rel in self.relations if rel.entry_id == entry_id]

    @override
    def unlink_entry_resource(self, entry_id: str, resource_id: str) -> None:
        # Mutate the shared state list in place so the DatabaseState reference and
        # this repo's view never diverge.
        self.relations[:] = [
            rel for rel in self.relations if not (rel.entry_id == entry_id and rel.resource_id == resource_id)
        ]

    def unlink_entry(self, entry_id: str) -> list[ResourceEntry]:
        removed = [rel for rel in self.relations if rel.entry_id == entry_id]
        self.relations[:] = [rel for rel in self.relations if rel.entry_id != entry_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        if not where:
            removed = list(self.relations)
            self.relations.clear()
            return removed
        removed = [rel for rel in self.relations if matches_where(rel, where)]
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [rel for rel in self.relations if rel.id not in removed_ids]
        return removed


__all__ = ["InMemoryResourceEntryRepository"]
