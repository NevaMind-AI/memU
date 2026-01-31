from __future__ import annotations

import logging
from typing import Any, Literal

from sqlalchemy import create_engine, inspect

from memu.database.mysql.schema import get_metadata

logger = logging.getLogger(__name__)

DDLMode = Literal["create", "validate"]


def run_migrations(*, dsn: str, scope_model: type[Any], ddl_mode: DDLMode = "create") -> None:
    """
    Run database migrations based on the ddl_mode setting.

    Args:
        dsn: Database connection string (mysql+pymysql://user:pass@host/db)
        scope_model: User scope model for scoped tables
        ddl_mode: "create" to create missing tables, "validate" to only check schema
    """
    metadata = get_metadata(scope_model)
    engine = create_engine(dsn)

    if ddl_mode == "create":
        # Create all tables that don't exist
        metadata.create_all(engine)
        logger.info("MySQL database tables created/verified")
    elif ddl_mode == "validate":
        # Validate that all expected tables exist
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = set(metadata.tables.keys())
        missing_tables = expected_tables - existing_tables

        if missing_tables:
            msg = f"Database schema validation failed. Missing tables: {sorted(missing_tables)}"
            raise RuntimeError(msg)
        logger.info("MySQL database schema validated successfully")


__all__ = ["DDLMode", "run_migrations"]
