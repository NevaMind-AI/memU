"""Shared ``MEMU_*`` configuration — one loader, every entrypoint.

The ``memu`` CLI, the ``memu-<host>`` adapters, and the bridging pipeline all
construct their :class:`~memu.app.MemoryService` here. That sharing is not
tidiness: the *record* seam (bridging writes) and the *inject* seam (retrieval
reads) must agree on the DSN **and** the embedding provider, or a query is
embedded in one space and compared against vectors written in another — the
comparison is meaningless and retrieval silently returns nothing (ADR 0009).

Values resolve in this order:

1. the process environment (``MEMU_DB=… memu retrieve …`` wins, so a one-off
   override needs no file edit);
2. ``~/.memu/config.env`` — a dotenv written once at install time. Scheduled
   tasks run with no reliable working directory and do not inherit an
   interactive shell, so a file at a known absolute path is the only robust
   carrier; a ``export`` in a shell profile is not.
3. the default argument, where one exists.

:func:`require` deliberately has no default. Missing required config must
surface, not silently fall back — a bridging run that defaults to
``./data/memu.sqlite3`` while retrieval reads the configured store "succeeds"
and finds nothing, which is the exact failure this module exists to prevent.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

CONFIG_ENV = "~/.memu/config.env"
"""Where install persists the collected values. Override with ``MEMU_CONFIG_ENV``."""


class ConfigError(RuntimeError):
    """Required ``MEMU_*`` configuration is absent or unusable."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"{name} is not set. Add it to {CONFIG_ENV} (or export it). Refusing to fall back to a "
            f"default: record and retrieval must use the same store, or retrieval finds nothing."
        )


@cache
def _file_values() -> dict[str, str]:
    """Parse the dotenv. Cached: entrypoint processes are short-lived."""
    path = Path(os.path.expanduser(os.environ.get("MEMU_CONFIG_ENV", CONFIG_ENV)))
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip().strip("\"'")
    return values


def reload() -> None:
    """Drop the cached dotenv — for tests, and for a process that rewrites it."""
    _file_values.cache_clear()


def env(name: str, default: str | None = None) -> str | None:
    """Look up ``name``: process environment, then the dotenv, then ``default``."""
    return os.environ.get(name) or _file_values().get(name) or default


def require(name: str) -> str:
    """Like :func:`env`, but raise rather than guess."""
    value = env(name)
    if not value:
        raise ConfigError(name)
    return value


def database_config(db: str) -> dict[str, Any]:
    """Turn a ``MEMU_DB`` value into a ``database_config`` mapping.

    Accepts a bare SQLite path (``./data/memu.sqlite3``), a full SQLAlchemy URL
    (``sqlite:///…``, ``postgres://…``), or the in-memory sentinel.
    """
    if db in (":memory:", "inmemory"):
        return {"metadata_store": {"provider": "inmemory"}}
    if db.startswith(("postgres://", "postgresql://")):
        return {"metadata_store": {"provider": "postgres", "dsn": db}}
    if db.startswith("sqlite://"):
        return {"metadata_store": {"provider": "sqlite", "dsn": db}}
    path = Path(db).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return {"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{path}"}}


def embedding_provider() -> str:
    """The embedding provider id. There is no LLM in memU — this names the only
    model capability left, so ``MEMU_EMBED_PROVIDER`` is the primary variable;
    ``MEMU_LLM_PROVIDER`` is read as a fallback so existing ``~/.memu/config.env``
    files keep working."""
    return env("MEMU_EMBED_PROVIDER") or env("MEMU_LLM_PROVIDER") or "openai"


def embedding_profile() -> dict[str, Any]:
    """The ``default`` embedding profile — provider plus any overrides that are set."""
    profile: dict[str, Any] = {"provider": embedding_provider()}
    for key, var in (("embed_model", "MEMU_EMBED_MODEL"), ("base_url", "MEMU_BASE_URL"), ("api_key", "MEMU_API_KEY")):
        if value := env(var):
            profile[key] = value
    return profile


def build_service_from_env() -> Any:
    """Construct a :class:`MemoryService` purely from ``MEMU_*`` config.

    The flagless counterpart to the CLI's ``_build_service``: host adapters and
    scheduled tasks have no argv to read, so ``MEMU_DB`` is *required* here —
    there is no cwd-relative default to fall back to, and guessing one would
    silently split the store in two.
    """
    from memu.app import MemoryService

    return MemoryService(
        embedding_profiles={"default": embedding_profile()},
        database_config=database_config(require("MEMU_DB")),
    )
