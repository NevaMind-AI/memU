from __future__ import annotations

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool

from memu.database.postgres.schema import get_metadata

config = context.config

if config.config_file_name is not None:  # pragma: no cover - alembic bootstrap
    fileConfig(config.config_file_name)


def get_target_metadata() -> MetaData | None:
    scope_model = config.attributes.get("scope_model")
    return get_metadata(scope_model)


target_metadata: MetaData | None = get_target_metadata()


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Only manage tables declared in our metadata.

    Keeps autogenerate from emitting drops for unrelated tables when the
    reflection target happens to share a schema with other applications.
    """
    if type_ == "table" and target_metadata is not None:
        return name in target_metadata.tables
    return True


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    """Keep generated revisions self-contained (no app-model imports)."""
    if type_ == "type":
        module = obj.__class__.__module__
        if module.startswith("pgvector."):
            autogen_context.imports.add("import pgvector.sqlalchemy")
            return f"pgvector.sqlalchemy.{obj!r}"
        # TZDateTime is just a timezone-aware DateTime; render it as such so
        # the migration does not have to import memu app modules.
        if obj.__class__.__name__ == "TZDateTime":
            return "sa.DateTime(timezone=True)"
        # SQLModel's AutoString (used for scope str columns) is a plain VARCHAR;
        # render it as sa.String() for parity with the other string columns and
        # to avoid an extra sqlmodel import in the migration.
        if module.startswith("sqlmodel.") and obj.__class__.__name__ == "AutoString":
            return "sa.String()"
    return False


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_name=include_name,
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = {"sqlalchemy.url": config.get_main_option("sqlalchemy.url")}
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_name=include_name,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
