from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import create_engine, inspect, text

from memu.database.postgres.schema import get_metadata

try:  # Optional dependency for Postgres backend
    from alembic import command
    from alembic.config import Config as AlembicConfig
except ImportError as exc:  # pragma: no cover - optional dependency
    msg = "alembic is required for Postgres migrations"
    raise ImportError(msg) from exc

logger = logging.getLogger(__name__)

DDLMode = Literal["create", "validate"]


def make_alembic_config(*, dsn: str, scope_model: type[Any]) -> AlembicConfig:
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    cfg.set_main_option("sqlalchemy.url", dsn)
    cfg.attributes["scope_model"] = scope_model
    return cfg


def run_migrations(*, dsn: str, scope_model: type[Any], ddl_mode: DDLMode = "create") -> None:
    """
    Run database migrations based on the ddl_mode setting.

    Args:
        dsn: Database connection string
        scope_model: User scope model for scoped tables
        ddl_mode: "create" to create missing tables, "validate" to only check schema
    """
    metadata = get_metadata(scope_model)
    engine = create_engine(dsn)

    if ddl_mode == "create":
        # Enable pgvector extension if needed (requires superuser or extension already installed)
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("pgvector extension enabled")
            except Exception as e:
                # Check if extension already exists
                result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).fetchone()
                if result:
                    logger.info("pgvector extension already installed")
                else:
                    msg = (
                        "Failed to create pgvector extension. "
                        "Please run 'CREATE EXTENSION vector;' as a superuser first."
                    )
                    raise RuntimeError(msg) from e

        # Create all tables that don't exist
        metadata.create_all(engine)
        logger.info("Database tables created/verified")
    elif ddl_mode == "validate":
        # Validate that all expected tables exist
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = set(metadata.tables.keys())
        missing_tables = expected_tables - existing_tables

        if missing_tables:
            msg = f"Database schema validation failed. Missing tables: {sorted(missing_tables)}"
            raise RuntimeError(msg)
        logger.info("Database schema validated successfully")

    # Run any pending Alembic migrations
    cfg = make_alembic_config(dsn=dsn, scope_model=scope_model)
    command.upgrade(cfg, "head")


__all__ = ["DDLMode", "make_alembic_config", "run_migrations"]
