from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.database.interfaces import Database


class AgenticMixin:
    if TYPE_CHECKING:
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _normalize_where: Callable[[Mapping[str, Any] | None], dict[str, Any]]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _ensure_categories_ready: Callable[[Context, Database, Mapping[str, Any] | None], Awaitable[None]]

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List RecallFiles across every track without workflow orchestration.

        Unlike :meth:`CRUDMixin.list_recall_files`, this does not force the
        ``track="memory"`` filter (ADR 0006), so skill-track files are included,
        and it queries the repository directly instead of running a workflow.
        """
        store = self._get_database()
        where_filters = self._normalize_where(where)
        categories = store.recall_file_repo.list_categories(where_filters)
        categories_list = [self._model_dump_without_embeddings(category) for category in categories.values()]
        return {"categories": categories_list}
