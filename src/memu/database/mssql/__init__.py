from __future__ import annotations

from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.mssql.mssql import MssqlStore


def build_mssql_database(
    *,
    config: DatabaseConfig,
    user_model: type[BaseModel],
) -> MssqlStore:
    dsn = config.metadata_store.dsn
    if not dsn:
        msg = "MSSQL metadata_store requires a DSN"
        raise ValueError(msg)

    # MSSQL doesn't typically use pgvector, but we follow the pattern
    # The MssqlStore implementation handles vector_provider arg.
    vector_provider = config.vector_index.provider if config.vector_index else None

    # We no longer import SQLAModels/get_sqlalchemy_models from postgres here
    # MssqlStore internally builds its own models using SQLite/generic logic.

    return MssqlStore(
        dsn=dsn,
        ddl_mode=config.metadata_store.ddl_mode,
        vector_provider=vector_provider,
        scope_model=user_model,
        # sqla_models/models arguments are optional and MssqlStore will generate them.
    )


__all__ = ["MssqlStore", "build_mssql_database"]
