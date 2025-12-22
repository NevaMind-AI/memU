from __future__ import annotations

import logging
from typing import Any

try:  # Optional dependency for Postgres backend
    from sqlmodel import Session, create_engine
except ImportError as exc:  # pragma: no cover - optional dependency
    msg = "sqlmodel is required for Postgres storage support"
    raise ImportError(msg) from exc

logger = logging.getLogger(__name__)


class SessionManager:
    """Handle engine lifecycle and session creation for Postgres store."""

    def __init__(self, *, dsn: str, engine_kwargs: dict[str, Any] | None = None) -> None:
        kw = {"pool_pre_ping": True}
        if engine_kwargs:
            kw.update(engine_kwargs)
        self._engine = create_engine(dsn, **kw)

    def session(self) -> Session:
        return Session(self._engine, expire_on_commit=False)

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:
            logger.exception("Failed to close Postgres engine")


__all__ = ["SessionManager"]
