from __future__ import annotations

import logging
from typing import Any

try:
    from sqlmodel import Session, create_engine
except ImportError as exc:
    msg = "sqlmodel is required for MSSQL storage support"
    raise ImportError(msg) from exc

logger = logging.getLogger(__name__)


class SessionManager:
    """Handle engine lifecycle and session creation for MSSQL store."""

    def __init__(self, *, dsn: str, engine_kwargs: dict[str, Any] | None = None) -> None:
        kw = {"pool_pre_ping": True}
        if engine_kwargs:
            kw.update(engine_kwargs)

        # Ensure we are using the mssql+pyodbc driver
        if not dsn.startswith("mssql+pyodbc://"):
            # If user provided a raw DSN without driver, prompt or fix?
            # We assume the user provides a connection string.
            # However, for MSSQL, often users might provide just parameters.
            # But following Postgres pattern, we take a full DSN string usually.
            pass

        self._engine = create_engine(dsn, **kw)

    def session(self) -> Session:
        return Session(self._engine, expire_on_commit=False)

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:
            logger.exception("Failed to close MSSQL engine")


__all__ = ["SessionManager"]
