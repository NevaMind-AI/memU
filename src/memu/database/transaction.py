"""Atomic repository operations over an existing SQLAlchemy session."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy import text
from sqlmodel import Session

from memu.database.state import DatabaseState


class _BorrowedSession:
    """Make repository-level commits flush while the owning transaction is open."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> _BorrowedSession:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def commit(self) -> None:
        self._session.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)


class AtomicSessionManager:
    """Coordinates SQLite repository calls within one non-suspending transaction."""

    def __init__(self, *, engine: Any) -> None:
        self._engine = engine
        self._active: ContextVar[Session | None] = ContextVar(f"memu_transaction_{id(self)}", default=None)

    def session(self) -> Session | _BorrowedSession:
        active = self._active.get()
        return _BorrowedSession(active) if active is not None else Session(self._engine, expire_on_commit=False)

    @contextmanager
    def atomic(self) -> Iterator[None]:
        if self._active.get() is not None:
            msg = "Nested memU write transactions are not supported"
            raise RuntimeError(msg)
        with Session(self._engine, expire_on_commit=False) as session:
            session.execute(text("BEGIN IMMEDIATE"))
            token = self._active.set(session)
            try:
                yield
                session.commit()
            except BaseException:
                session.rollback()
                raise
            finally:
                self._active.reset(token)

    @contextmanager
    def snapshot(self) -> Iterator[None]:
        if self._active.get() is not None:
            msg = "Nested memU read transactions are not supported"
            raise RuntimeError(msg)
        with Session(self._engine, expire_on_commit=False) as session:
            session.execute(text("BEGIN"))
            token = self._active.set(session)
            try:
                yield
            finally:
                self._active.reset(token)
                session.rollback()


@contextmanager
def preserve_state(state: DatabaseState) -> Iterator[None]:
    """Restore repository caches after a failed unit of work."""
    with state.lock:
        # ponytail: copies the cache; use an undo log if cache size makes this costly.
        resources = copy.deepcopy(state.resources)
        recall_files = copy.deepcopy(state.recall_files)
        segments = copy.deepcopy(state.segments)
        try:
            yield
        except BaseException:
            state.resources.clear()
            state.resources.update(resources)
            state.recall_files.clear()
            state.recall_files.update(recall_files)
            state.segments[:] = segments
            raise
