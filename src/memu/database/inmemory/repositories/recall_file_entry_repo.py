from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import RecallFileEntry
from memu.database.repositories.recall_file_entry import RecallFileEntryRepo


class InMemoryFileEntryRepository(RecallFileEntryRepo):
    def __init__(self, *, state: InMemoryState, recall_file_entry_model: type[RecallFileEntry]) -> None:
        self._state = state
        self.recall_file_entry_model = recall_file_entry_model
        self.relations: list[RecallFileEntry] = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        if not where:
            return list(self.relations)
        return [rel for rel in self.relations if matches_where(rel, where)]

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> RecallFileEntry:
        _ = item_id  # enforced by caller via existing state
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel
        rel = self.recall_file_entry_model(id=str(uuid.uuid4()), item_id=item_id, category_id=cat_id, **user_data)
        self.relations.append(rel)
        return rel

    def load_existing(self) -> None:
        return None

    @override
    def get_item_categories(self, item_id: str) -> list[RecallFileEntry]:
        return [rel for rel in self.relations if rel.item_id == item_id]

    @override
    def unlink_item_category(self, item_id: str, cat_id: str) -> None:
        # Mutate the shared state list in place so the DatabaseState reference and
        # this repo's view never diverge (rebinding self.relations would orphan the
        # shared state.relations list).
        self.relations[:] = [
            rel for rel in self.relations if not (rel.item_id == item_id and rel.category_id == cat_id)
        ]

    def unlink_item(self, item_id: str) -> list[RecallFileEntry]:
        removed = [rel for rel in self.relations if rel.item_id == item_id]
        self.relations[:] = [rel for rel in self.relations if rel.item_id != item_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        if not where:
            removed = list(self.relations)
            self.relations.clear()
            return removed
        removed = [rel for rel in self.relations if matches_where(rel, where)]
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [rel for rel in self.relations if rel.id not in removed_ids]
        return removed


__all__ = ["InMemoryFileEntryRepository"]
