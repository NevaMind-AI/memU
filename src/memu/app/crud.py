from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.database.interfaces import Database


class CRUDMixin:
    if TYPE_CHECKING:
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]
        user_model: type[BaseModel]

    async def list_memory_items(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = self._get_context()
        store = self._get_database()
        where_filters = self._normalize_where(where)

        state: WorkflowState = {
            "ctx": ctx,
            "store": store,
            "where": where_filters,
        }

        result = await self._run_workflow("crud_list_memory_items", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "List memory items workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def list_memory_categories(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = self._get_context()
        store = self._get_database()
        where_filters = self._normalize_where(where)

        state: WorkflowState = {
            "ctx": ctx,
            "store": store,
            "where": where_filters,
        }
        result = await self._run_workflow("crud_list_memory_categories", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "List memory categories workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _build_list_memory_items_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="list_memory_items",
                role="read_memories",
                handler=self._crud_list_memory_items,
                requires={"ctx", "store", "where"},
                produces={"items"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._crud_build_list_items_response,
                requires={"items", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_list_memory_items_initial_keys() -> set[str]:
        return {
            "ctx",
            "store",
            "where",
        }

    def _build_list_memory_categories_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="list_memory_categories",
                role="read_categories",
                handler=self._crud_list_memory_categories,
                requires={"ctx", "store", "where"},
                produces={"categories"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._crud_build_list_categories_response,
                requires={"categories", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    def _normalize_where(self, where: Mapping[str, Any] | None) -> dict[str, Any]:
        """Validate and clean the `where` scope filters against the configured user model."""
        if not where:
            return {}

        valid_fields = set(getattr(self.user_model, "model_fields", {}).keys())
        cleaned: dict[str, Any] = {}

        for raw_key, value in where.items():
            if value is None:
                continue
            field = raw_key.split("__", 1)[0]
            if field not in valid_fields:
                msg = f"Unknown filter field '{field}' for current user scope"
                raise ValueError(msg)
            cleaned[raw_key] = value

        return cleaned

    def _crud_list_memory_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        items = store.memory_item_repo.list_items(where_filters)
        state["items"] = items
        return state

    def _crud_list_memory_categories(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        categories = store.memory_category_repo.list_categories(where_filters)
        state["categories"] = categories
        return state

    def _crud_build_list_items_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        items = state["items"]
        items_list = [self._model_dump_without_embeddings(item) for item in items.values()]
        response = {
            "items": items_list,
        }
        state["response"] = response
        return state

    def _crud_build_list_categories_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        categories = state["categories"]
        categories_list = [self._model_dump_without_embeddings(category) for category in categories.values()]
        response = {
            "categories": categories_list,
        }
        state["response"] = response
        return state
