from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import RecallFileResource
from memu.database.repositories.recall_file_resource import RecallFileResourceRepo


class InMemoryFileResourceRepository(RecallFileResourceRepo):
    def __init__(self, *, state: InMemoryState, recall_file_resource_model: type[RecallFileResource]) -> None:
        self._state = state
        self.recall_file_resource_model = recall_file_resource_model
        self.relations: list[RecallFileResource] = self._state.resource_relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileResource]:
        if not where:
            return list(self.relations)
        return [rel for rel in self.relations if matches_where(rel, where)]

    def link_resource_category(self, resource_id: str, cat_id: str, user_data: dict[str, Any]) -> RecallFileResource:
        _ = resource_id  # enforced by caller via existing state
        for rel in self.relations:
            if rel.resource_id == resource_id and rel.file_id == cat_id:
                return rel
        rel = self.recall_file_resource_model(
            id=str(uuid.uuid4()), resource_id=resource_id, file_id=cat_id, **user_data
        )
        self.relations.append(rel)
        return rel

    def load_existing(self) -> None:
        return None

    @override
    def get_resource_categories(self, resource_id: str) -> list[RecallFileResource]:
        return [rel for rel in self.relations if rel.resource_id == resource_id]

    @override
    def unlink_resource_category(self, resource_id: str, cat_id: str) -> None:
        # Mutate the shared state list in place so the DatabaseState reference and
        # this repo's view never diverge (rebinding self.relations would orphan the
        # shared state.resource_relations list).
        self.relations[:] = [
            rel for rel in self.relations if not (rel.resource_id == resource_id and rel.file_id == cat_id)
        ]

    def unlink_resource(self, resource_id: str) -> list[RecallFileResource]:
        removed = [rel for rel in self.relations if rel.resource_id == resource_id]
        self.relations[:] = [rel for rel in self.relations if rel.resource_id != resource_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileResource]:
        if not where:
            removed = list(self.relations)
            self.relations.clear()
            return removed
        removed = [rel for rel in self.relations if matches_where(rel, where)]
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [rel for rel in self.relations if rel.id not in removed_ids]
        return removed


__all__ = ["InMemoryFileResourceRepository"]
