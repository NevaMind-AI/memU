from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import create_engine, inspect

try:  # Optional dependency for Postgres backend
    from alembic import command
    from alembic.config import Config as AlembicConfig
except ImportError as exc:  # pragma: no cover - optional dependency
    msg = "alembic is required for Postgres migrations"
    raise ImportError(msg) from exc

logger = logging.getLogger(__name__)

DDLMode = Literal["create", "validate"]
_UNESCAPED_CONFIGPARSER_PERCENT = re.compile(r"(?<!%)%(?!%)")


def _escape_for_config_parser(value: str) -> str:
    return _UNESCAPED_CONFIGPARSER_PERCENT.sub("%%", value)


def make_alembic_config(*, dsn: str, scope_model: type[Any]) -> AlembicConfig:
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    cfg.set_main_option("sqlalchemy.url", _escape_for_config_parser(dsn))
    cfg.attributes["scope_model"] = scope_model
    return cfg


def run_migrations(*, dsn: str, scope_model: type[Any], ddl_mode: DDLMode = "create") -> None:
    """
    Run database migrations based on the ddl_mode setting.

    Args:
        dsn: Database connection string
        scope_model: User scope model for scoped tables
        ddl_mode: "create" to apply migrations up to head, "validate" to only check schema

    Alembic is the source of truth for schema: "create" runs ``upgrade head``
    rather than ``metadata.create_all`` so that a fresh database is built from
    the committed revisions. The pgvector extension is enabled by the initial
    revision, so no separate bootstrap step is required here.
    """
    from memu.database.postgres.schema import get_metadata

    if ddl_mode == "create":
        cfg = make_alembic_config(dsn=dsn, scope_model=scope_model)
        command.upgrade(cfg, "head")
        logger.info("Database migrated to head")
    elif ddl_mode == "validate":
        metadata = get_metadata(scope_model)
        engine = create_engine(dsn)
        try:
            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())
            expected_tables = set(metadata.tables.keys())
            missing_tables = expected_tables - existing_tables

            if missing_tables:
                msg = f"Database schema validation failed. Missing tables: {sorted(missing_tables)}"
                raise RuntimeError(msg)
            logger.info("Database schema validated successfully")
        finally:
            engine.dispose()


__all__ = ["DDLMode", "make_alembic_config", "run_migrations"]
