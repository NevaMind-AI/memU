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


class AsyncSessionManager:
    """Handle async engine lifecycle and session creation for Postgres store using asyncpg."""

    def __init__(self, *, dsn: str, engine_kwargs: dict[str, Any] | None = None) -> None:
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "sqlalchemy[asyncio] is required for async Postgres storage support"
            raise ImportError(msg) from exc

        kw = {"pool_pre_ping": True}
        if engine_kwargs:
            kw.update(engine_kwargs)

        async_dsn = self._convert_to_async_dsn(dsn)
        self._engine = create_async_engine(async_dsn, **kw)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @staticmethod
    def _convert_to_async_dsn(dsn: str) -> str:
        if dsn.startswith("postgresql://"):
            return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        if dsn.startswith("postgres://"):
            return dsn.replace("postgres://", "postgresql+asyncpg://", 1)
        return dsn

    def session(self) -> Any:
        return self._session_factory()

    async def close(self) -> None:
        try:
            await self._engine.dispose()
        except Exception:
            logger.exception("Failed to close async Postgres engine")


__all__ = ["SessionManager", "AsyncSessionManager"]
