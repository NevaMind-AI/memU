"""Shared ``MEMU_*`` configuration — one loader, every entrypoint.

The ``memu`` CLI, the ``memu-<host>`` adapters, and the bridging pipeline all
select their agentic backend here. That sharing is not tidiness: the *record*
seam (bridging writes) and the *inject* seam (retrieval reads) must agree on
local versus cloud execution. In local mode they must also agree on the DSN
**and** embedding provider, or a query is embedded in one space and compared
against vectors written in another — the comparison is meaningless and
retrieval silently returns nothing (ADR 0009/0012).

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
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from memu.agentic_backend import AgenticMemoryBackend

CONFIG_ENV = "~/.memu/config.env"
"""Where install persists the collected values. Override with ``MEMU_CONFIG_ENV``."""


class ConfigError(RuntimeError):
    """Required ``MEMU_*`` configuration is absent or unusable."""

    def __init__(self, name: str, detail: str | None = None) -> None:
        if detail is not None:
            super().__init__(f"{name}: {detail}")
            return
        super().__init__(
            f"{name} is not set. Add it to {CONFIG_ENV} (or export it). Refusing to fall back to a "
            f"default: record and retrieval must use the same store, or retrieval finds nothing."
        )


_ENV_PASSTHROUGH = ("NO_PROXY", "no_proxy")
"""Non-``MEMU_*`` keys that ``config.env`` carries into the process environment.

The guides call the file "the carrier" — a scheduled task has no interactive
shell to inherit from — and a proxy exemption is exactly the kind of
machine-local fact that must reach the HTTP stack, which reads ``NO_PROXY``
from the environment and knows nothing of memU's config. Narrow allowlist on
purpose; ``setdefault`` only, so a value already in the environment wins."""


@cache
def _file_values() -> dict[str, str]:
    """Parse the dotenv. Cached: entrypoint processes are short-lived.

    Side effect, once per process: keys in :data:`_ENV_PASSTHROUGH` found in
    the file are exported to ``os.environ`` (without overriding existing
    values), so ``NO_PROXY`` written next to the ``MEMU_*`` settings actually
    reaches httpx.
    """
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
    for key in _ENV_PASSTHROUGH:
        if key in values:
            os.environ.setdefault(key, values[key])
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


MemoryMode = Literal["local", "cloud"]


def memory_mode() -> MemoryMode:
    """Resolve the execution backend, defaulting to local for compatibility."""
    value = (env("MEMU_MEMORY_MODE", "local") or "local").strip().lower()
    if value == "local":
        return "local"
    if value == "cloud":
        return "cloud"
    raise ConfigError("MEMU_MEMORY_MODE", "must be either 'local' or 'cloud'")


def cloud_base_url() -> str:
    """The full v4 memory API base URL, including ``/api/v4/memory/``."""
    from memu.cloud import DEFAULT_CLOUD_BASE_URL

    return env("MEMU_CLOUD_BASE_URL", DEFAULT_CLOUD_BASE_URL) or DEFAULT_CLOUD_BASE_URL


def cloud_api_key() -> str:
    """Resolve the project API key without reusing local embedding credentials."""
    value = env("MEMU_CLOUD_API_KEY")
    if not value:
        raise ConfigError(
            "MEMU_CLOUD_API_KEY",
            f"is required in cloud mode. Add it to {CONFIG_ENV} (or export it)",
        )
    return value


def build_agentic_memory_backend_from_env(
    *,
    local_database: str | None = None,
    local_embedding_profile: dict[str, Any] | None = None,
) -> AgenticMemoryBackend:
    """Build the configured local service or cloud client through one selector.

    ``memu`` passes its existing local CLI flag overrides. Host adapters pass no
    overrides and therefore require the install-time ``MEMU_DB`` configuration
    in local mode. Cloud mode ignores local-only overrides.
    """
    if memory_mode() == "cloud":
        from memu.cloud import CloudMemoryClient

        return CloudMemoryClient(
            base_url=cloud_base_url(),
            api_key=cloud_api_key(),
        )

    from memu.app import MemoryService

    resolved_database = database_config(local_database if local_database is not None else require("MEMU_DB"))
    resolved_embedding = local_embedding_profile if local_embedding_profile is not None else embedding_profile()
    return MemoryService(
        embedding_profiles={"default": resolved_embedding},
        database_config=resolved_database,
    )


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
