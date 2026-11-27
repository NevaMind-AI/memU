"""Public TOML names for the existing environment-variable interface."""

from __future__ import annotations

import math
import os
from typing import Any

KEYS = {
    "MEMU_MEMORY_MODE": "mode",
    "MEMU_DB": "local.db",
    "MEMU_CLOUD_API_KEY": "cloud.api_key",
    "MEMU_CLOUD_BASE_URL": "cloud.base_url",
    "MEMU_EMBED_PROVIDER": "embedding.provider",
    "MEMU_EMBED_MODEL": "embedding.model",
    "MEMU_API_KEY": "embedding.api_key",
    "MEMU_BASE_URL": "embedding.base_url",
    "MEMU_EMBED_BATCH_SIZE": "embedding.batch_size",
    "MEMU_HTTP_PROXY": "network.proxy",
    "NO_PROXY": "network.no_proxy",
    "no_proxy": "network.no_proxy_lowercase",
    "MEMU_QUERY_EXTRACT_ENABLED": "retrieval.extract_query",
    "MEMU_TELEMETRY": "telemetry.enabled",
    "MEMU_EVENTS_BASE_URL": "telemetry.base_url",
    "MEMU_EVENTS_SPOOL": "telemetry.spool",
    "MEMU_EVENTS_DEBUG": "telemetry.debug",
    "MEMU_DEBUG": "debug",
    "MEMU_PI_RECALL_SYNC": "hosts.pi.recall_sync",
    "MEMU_COWORK_ROOTS": "hosts.cowork.roots",
    "MEMU_DOCS_BASE_URL": "sources.docs",
    "MEMU_TEMPLATE_BASE_URL": "sources.templates",
}
for _backend in ("cloud", "local"):
    for _kind in ("short", "long", "extracted"):
        KEYS[f"MEMU_{_backend.upper()}_RETRIEVE_MIN_SCORE_{_kind.upper()}"] = f"retrieval.{_backend}.min_score.{_kind}"

BOOLS = {"MEMU_PI_RECALL_SYNC", "MEMU_QUERY_EXTRACT_ENABLED", "MEMU_TELEMETRY", "MEMU_EVENTS_DEBUG", "MEMU_DEBUG"}
SCORES = {key for key in KEYS if "_MIN_SCORE_" in key}


def typed_value(key: str, value: str) -> Any:
    """Convert only supported forms; never guess a different effective setting."""
    if not value:
        return value
    if key in BOOLS:
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"Invalid boolean for {key}")  # noqa: TRY003
    if key in SCORES:
        score = float(value)
        if not math.isfinite(score) or not -1 <= score <= 1:
            raise ValueError(f"Invalid score for {key}")  # noqa: TRY003
        return score
    if key == "MEMU_EMBED_BATCH_SIZE":
        size = int(value)
        if size < 1:
            raise ValueError(f"Invalid batch size for {key}")  # noqa: TRY003
        return size
    if key == "MEMU_COWORK_ROOTS":
        return [root.strip() for root in value.split(os.pathsep) if root.strip()]
    return value


def env_value(key: str, value: Any) -> str:
    """Validate TOML types before adapting them to the shared string API."""
    if value == "":
        return ""
    if key in BOOLS and type(value) is bool:
        return "1" if value else "0"
    if key in SCORES and type(value) in (int, float):
        result = str(value)
        typed_value(key, result)
        return result
    if key == "MEMU_EMBED_BATCH_SIZE" and type(value) is int:
        result = str(value)
        typed_value(key, result)
        return result
    if key == "MEMU_COWORK_ROOTS" and isinstance(value, list) and all(isinstance(v, str) for v in value):
        return os.pathsep.join(value)
    if key not in BOOLS | SCORES | {"MEMU_EMBED_BATCH_SIZE", "MEMU_COWORK_ROOTS"} and isinstance(value, str):
        return value
    raise ValueError(f"Invalid type for {KEYS[key]}")  # noqa: TRY003
