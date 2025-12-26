from __future__ import annotations

from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.inmemory.models import build_inmemory_models
from memu.database.inmemory.repo import InMemoryStore


def build_inmemory_database(
    *,
    config: DatabaseConfig,
    user_model: type[BaseModel],
) -> InMemoryStore:
    resource_model, memory_category_model, memory_item_model, category_item_model = build_inmemory_models(user_model)
    return InMemoryStore(
        scope_model=user_model,
        resource_model=resource_model,
        memory_item_model=memory_item_model,
        memory_category_model=memory_category_model,
        category_item_model=category_item_model,
    )


__all__ = ["build_inmemory_database"]
