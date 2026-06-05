from __future__ import annotations

import os
from pathlib import PureWindowsPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.service import MemoryService


def build_memory_service_from_env() -> "MemoryService":
    """Build a MemoryService from MEMU_* environment variables."""

    from memu.app.service import MemoryService

    return MemoryService(**_memory_service_kwargs_from_env())


def _memory_service_kwargs_from_env() -> dict[str, Any]:
    from memu.app.settings import default_api_key_env

    provider = _env_choice("MEMU_LLM_PROVIDER", "openai")
    client_backend = _env_choice("MEMU_LLM_CLIENT_BACKEND", "sdk", choices=("httpx", "sdk", "lazyllm_backend"))
    llm_profile: dict[str, Any] = {
        "provider": provider,
        "client_backend": client_backend,
        "api_key": _env_value("MEMU_API_KEY_ENV", default_api_key_env(provider)),
        "chat_model": _env_value("MEMU_CHAT_MODEL", "gpt-4o-mini"),
        "embed_model": _env_value("MEMU_EMBED_MODEL", "text-embedding-3-small"),
        "embed_batch_size": _env_int("MEMU_EMBED_BATCH_SIZE", 1, min_value=1),
    }
    if base_url := _env_value("MEMU_LLM_BASE_URL", ""):
        llm_profile["base_url"] = base_url

    database_provider = _env_choice("MEMU_DATABASE_PROVIDER", "inmemory", choices=("inmemory", "sqlite", "postgres"))
    database_config: dict[str, Any] = {
        "metadata_store": {
            "provider": database_provider,
            "ddl_mode": _env_choice("MEMU_DATABASE_DDL_MODE", "create", choices=("create", "validate")),
        }
    }
    dsn = _env_value("MEMU_DATABASE_DSN", "") or _sqlite_dsn_from_env(database_provider)
    if database_provider == "postgres" and not dsn:
        msg = "MEMU_DATABASE_DSN is required when MEMU_DATABASE_PROVIDER=postgres"
        raise ValueError(msg)
    if dsn:
        database_config["metadata_store"]["dsn"] = dsn

    vector_provider = _env_optional_choice("MEMU_VECTOR_PROVIDER", choices=("bruteforce", "pgvector", "none"))
    if _env_value("MEMU_VECTOR_DSN", ""):
        msg = "MEMU_VECTOR_DSN is not supported; pgvector uses MEMU_DATABASE_DSN"
        raise ValueError(msg)
    if vector_provider:
        if vector_provider == "pgvector" and database_provider != "postgres":
            msg = "MEMU_VECTOR_PROVIDER=pgvector requires MEMU_DATABASE_PROVIDER=postgres"
            raise ValueError(msg)
        database_config["vector_index"] = {"provider": vector_provider}

    return {
        "llm_profiles": {"default": llm_profile},
        "database_config": database_config,
        "retrieve_config": {"method": _env_choice("MEMU_RETRIEVE_METHOD", "rag", choices=("rag", "llm"))},
        "blob_config": {"resources_dir": _env_value("MEMU_RESOURCES_DIR", "./data/resources")},
    }


def _env_value(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_choice(name: str, default: str, *, choices: tuple[str, ...] | None = None) -> str:
    value = _env_value(name, default).lower()
    if choices is not None and value not in choices:
        msg = f"{name} must be one of: {', '.join(choices)}"
        raise ValueError(msg)
    return value


def _env_optional_choice(name: str, *, choices: tuple[str, ...]) -> str | None:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    return _env_choice(name, "", choices=choices)


def _env_int(name: str, default: int, *, min_value: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = int(raw_value.strip())
    except ValueError as exc:
        msg = f"{name} must be an integer"
        raise ValueError(msg) from exc
    if min_value is not None and value < min_value:
        msg = f"{name} must be >= {min_value}"
        raise ValueError(msg)
    return value


def _sqlite_dsn_from_env(provider: str) -> str | None:
    if provider != "sqlite":
        return None
    path = os.getenv("MEMU_SQLITE_PATH")
    if path is None or not path.strip():
        path = "./data/memu.db"
    return _sqlite_dsn_from_path(path)


def _sqlite_dsn_from_path(path: str) -> str:
    value = path.strip()
    if value.startswith("sqlite://"):
        return value
    if value == ":memory:":
        return "sqlite:///:memory:"
    if "\\" in value:
        value = PureWindowsPath(value).as_posix()
    return f"sqlite:///{value}"


__all__ = ["build_memory_service_from_env"]
