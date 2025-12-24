from __future__ import annotations

from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.inmemory import build_inmemory_database
from memu.database.interfaces import Database
from memu.database.postgres import build_postgres_database


def build_database(
    *,
    config: DatabaseConfig,
    user_model: type[BaseModel],
) -> Database:
    """
    Initialize a database backend for the configured provider.
    """
    provider = config.metadata_store.provider
    if provider == "inmemory":
        return build_inmemory_database(config=config, user_model=user_model)
    elif provider == "postgres":
        return build_postgres_database(config=config, user_model=user_model)
    else:
        msg = f"Unsupported metadata_store provider: {provider}"
        raise ValueError(msg)
