from __future__ import annotations

import logging
from typing import Any

try:
    from sqlmodel import Session, create_engine
except ImportError as exc:
    msg = "sqlmodel is required for Oracle storage support"
    raise ImportError(msg) from exc

import importlib.util

if not importlib.util.find_spec("oracledb"):
    msg = "oracledb is required for Oracle storage support"
    raise ImportError(msg)

logger = logging.getLogger(__name__)


class SessionManager:
    """Handle engine lifecycle and session creation for Oracle store."""

    def __init__(self, *, dsn: str, engine_kwargs: dict[str, Any] | None = None) -> None:
        kw = {"pool_pre_ping": True}
        # Oracle specific optimizations can be added here
        if engine_kwargs:
            kw.update(engine_kwargs)
        self._engine = create_engine(dsn, **kw)

    def session(self) -> Session:
        return Session(self._engine, expire_on_commit=False)

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:
            logger.exception("Failed to close Oracle engine")


__all__ = ["SessionManager"]
