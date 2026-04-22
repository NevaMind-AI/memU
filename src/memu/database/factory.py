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

    Supported metadata providers:
        - "inmemory": In-memory storage (default, no persistence)
        - "postgres": PostgreSQL with optional pgvector support
        - "sqlite": SQLite file-based storage (lightweight, portable)

    Supported vector index providers (used together with a metadata provider):
        - "bruteforce": In-memory cosine top-k (default)
        - "pgvector": PostgreSQL pgvector column in the metadata backend
        - "milvus": External Milvus / Milvus Lite / Zilliz Cloud index
        - "none": Disable vector search entirely
    """
    vector_index = build_vector_index(config.vector_index)

    provider = config.metadata_store.provider
    if provider == "inmemory":
        return build_inmemory_database(
            config=config,
            user_model=user_model,
            vector_index=vector_index,
        )
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
