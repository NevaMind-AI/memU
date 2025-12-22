from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # Optional dependency for Postgres backend
    from alembic import command
    from alembic.config import Config as AlembicConfig
except ImportError as exc:  # pragma: no cover - optional dependency
    msg = "alembic is required for Postgres migrations"
    raise ImportError(msg) from exc


def make_alembic_config(*, dsn: str, scope_model: type[Any]) -> AlembicConfig:
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    cfg.set_main_option("sqlalchemy.url", dsn)
    cfg.attributes["scope_model"] = scope_model
    return cfg


def run_migrations(*, dsn: str, scope_model: type[Any]) -> None:
    cfg = make_alembic_config(dsn=dsn, scope_model=scope_model)
    command.upgrade(cfg, "head")


__all__ = ["make_alembic_config", "run_migrations"]
