from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.inmemory import build_inmemory_database
from memu.database.interfaces import Database
from memu.database.vector_index import build_vector_index

if TYPE_CHECKING:
    pass


def build_database(
    *,
    config: DatabaseConfig,
    user_model: type[BaseModel],
) -> Database:
    """
    Initialize a database backend for the configured provider.

    Supported providers:
        - "inmemory": In-memory storage (default, no persistence)
        - "postgres": PostgreSQL with optional pgvector support
        - "sqlite": SQLite file-based storage (lightweight, portable)
    """
    provider = config.metadata_store.provider
    vector_provider = config.vector_index.provider if config.vector_index else None
    if vector_provider == "milvus" and provider != "inmemory":
        msg = "vector_index provider 'milvus' currently supports metadata_store provider 'inmemory' only"
        raise ValueError(msg)

    if provider == "inmemory":
        vector_index = build_vector_index(config.vector_index)
        return build_inmemory_database(config=config, user_model=user_model, vector_index=vector_index)
    elif provider == "postgres":
        # Lazy import to avoid requiring pgvector when not using postgres
        from memu.database.postgres import build_postgres_database

        return build_postgres_database(config=config, user_model=user_model)
    elif provider == "sqlite":
        # Lazy import to avoid loading SQLite dependencies when not needed
        from memu.database.sqlite import build_sqlite_database

        return build_sqlite_database(config=config, user_model=user_model)
    else:
        msg = f"Unsupported metadata_store provider: {provider}"
        raise ValueError(msg)
