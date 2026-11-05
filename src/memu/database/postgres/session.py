from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from memu.database.transaction import AtomicSessionManager

try:  # Optional dependency for Postgres backend
    from sqlmodel import create_engine
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
        self._atomic_manager = AtomicSessionManager(engine=self._engine, dialect="postgres")

    def session(self) -> Any:
        return self._atomic_manager.session()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with self._atomic_manager.atomic():
            yield

    @contextmanager
    def snapshot(self) -> Iterator[None]:
        with self._atomic_manager.snapshot():
            yield

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:
            logger.exception("Failed to close Postgres engine")


__all__ = ["SessionManager"]
