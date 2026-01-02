from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any, cast, get_args

from pydantic import BaseModel

from memu.database.models import MemoryCategory, MemoryType
from memu.prompts.category_patch import CATEGORY_PATCH_PROMPT
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import PatchConfig
    from memu.database.interfaces import Database


class PatchMixin:
    if TYPE_CHECKING:
        patch_config: PatchConfig
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]
        user_model: type[BaseModel]
        _ensure_categories_ready: Callable[[Context, Database, Mapping[str, Any] | None], Awaitable[None]]

    async def create_memory_item(
        self,
        *,
        memory_type: MemoryType,
        memory_content: str,
        memory_categories: list[str],
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if memory_type not in get_args(MemoryType):
            msg = f"Invalid memory type: '{memory_type}', must be one of {get_args(MemoryType)}"
            raise ValueError(msg)

        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        state: WorkflowState = {
            "memory_payload": {
                "type": memory_type,
                "content": memory_content,
                "categories": memory_categories,
            },
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
        }

        result = await self._run_workflow("patch_create", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Create memory item workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def update_memory_item(
        self,
        *,
        memory_id: str,
        memory_type: MemoryType | None = None,
        memory_content: str | None = None,
        memory_categories: list[str] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if all((memory_type is None, memory_content is None, memory_categories is None)):
            msg = "At least one of memory type, memory content, or memory categories is required for UPDATE operation"
            raise ValueError(msg)
        if memory_type and memory_type not in get_args(MemoryType):
            msg = f"Invalid memory type: '{memory_type}', must be one of {get_args(MemoryType)}"
            raise ValueError(msg)

        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        state: WorkflowState = {
            "memory_id": memory_id,
            "memory_payload": {
                "type": memory_type,
                "content": memory_content,
                "categories": memory_categories,
            },
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
        }

        result = await self._run_workflow("patch_update", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Update memory item workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def delete_memory_item(
        self,
        *,
        memory_id: str,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        state: WorkflowState = {
            "memory_id": memory_id,
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
        }

        result = await self._run_workflow("patch_delete", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Delete memory item workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _build_create_memory_item_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="create_memory_item",
                role="patch",
                handler=self._patch_create_memory_item,
                requires={"memory_payload", "ctx", "store", "user"},
                produces={"memory_item", "category_updates"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._patch_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._patch_build_response,
                requires={"memory_item", "category_updates", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_create_memory_item_initial_keys() -> set[str]:
        return {
            "memory_payload",
            "ctx",
            "store",
            "user",
        }

    def _build_update_memory_item_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="update_memory_item",
                role="patch",
                handler=self._patch_update_memory_item,
                requires={"memory_id", "memory_payload", "ctx", "store", "user"},
                produces={"memory_item", "category_updates"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._patch_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._patch_build_response,
                requires={"memory_item", "category_updates", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_update_memory_item_initial_keys() -> set[str]:
        return {
            "memory_id",
            "memory_payload",
            "ctx",
            "store",
            "user",
        }

    def _build_delete_memory_item_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="delete_memory_item",
                role="patch",
                handler=self._patch_delete_memory_item,
                requires={"memory_id", "ctx", "store", "user"},
                produces={"memory_item", "category_updates"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._patch_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._patch_build_response,
                requires={"memory_item", "category_updates", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_delete_memory_item_initial_keys() -> set[str]:
        return {
            "memory_id",
            "ctx",
            "store",
            "user",
        }

    async def _patch_create_memory_item(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        memory_payload = state["memory_payload"]
        ctx = state["ctx"]
        store = state["store"]
        user = state["user"]
        category_memory_updates: dict[str, tuple[Any, Any]] = {}

        embed_payload = [memory_payload["content"]]
        content_embedding = (await self._get_llm_client().embed(embed_payload))[0]

        item = store.memory_item_repo.create_item(
            memory_type=memory_payload["type"],
            summary=memory_payload["content"],
            embedding=content_embedding,
            user_data=dict(user or {}),
        )
        cat_names = memory_payload["categories"]
        mapped_cat_ids = self._map_category_names_to_ids(cat_names, ctx)
        for cid in mapped_cat_ids:
            store.category_item_repo.link_item_category(item.id, cid, user_data=dict(user or {}))
            category_memory_updates[cid] = (None, memory_payload["content"])

        state.update({
            "memory_item": item,
            "category_updates": category_memory_updates,
        })
        return state

    async def _patch_update_memory_item(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        memory_id = state["memory_id"]
        memory_payload = state["memory_payload"]
        ctx = state["ctx"]
        store = state["store"]
        user = state["user"]
        category_memory_updates: dict[str, tuple[Any, Any]] = {}

        item = store.memory_item_repo.get_item(memory_id)
        if not item:
            msg = f"Memory item with id {memory_id} not found"
            raise ValueError(msg)
        old_content = item.summary
        old_item_categories = store.category_item_repo.get_item_categories(memory_id)
        mapped_old_cat_ids = [cat.category_id for cat in old_item_categories]

        if memory_payload["content"]:
            embed_payload = [memory_payload["content"]]
            content_embedding = (await self._get_llm_client().embed(embed_payload))[0]
        else:
            content_embedding = None

        if memory_payload["type"] or memory_payload["content"]:
            item = store.memory_item_repo.update_item(
                item_id=memory_id,
                memory_type=memory_payload["type"],
                summary=memory_payload["content"],
                embedding=content_embedding,
            )
        new_cat_names = memory_payload["categories"]
        mapped_new_cat_ids = self._map_category_names_to_ids(new_cat_names, ctx)

        cats_to_remove = set(mapped_old_cat_ids) - set(mapped_new_cat_ids)
        cats_to_add = set(mapped_new_cat_ids) - set(mapped_old_cat_ids)
        for cid in cats_to_remove:
            store.category_item_repo.unlink_item_category(memory_id, cid)
            category_memory_updates[cid] = (old_content, None)
        for cid in cats_to_add:
            store.category_item_repo.link_item_category(memory_id, cid, user_data=dict(user or {}))
            category_memory_updates[cid] = (None, item.summary)

        if memory_payload["content"]:
            for cid in set(mapped_old_cat_ids) & set(mapped_new_cat_ids):
                category_memory_updates[cid] = (old_content, item.summary)

        state.update({
            "memory_item": item,
            "category_updates": category_memory_updates,
        })
        return state

    async def _patch_delete_memory_item(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        memory_id = state["memory_id"]
        store = state["store"]
        category_memory_updates: dict[str, tuple[Any, Any]] = {}

        item = store.memory_item_repo.get_item(memory_id)
        if not item:
            msg = f"Memory item with id {memory_id} not found"
            raise ValueError(msg)
        item_categories = store.category_item_repo.get_item_categories(memory_id)
        for cat in item_categories:
            category_memory_updates[cat.category_id] = (item.summary, None)
        store.memory_item_repo.delete_item(memory_id)

        state.update({
            "memory_item": item,
            "category_updates": category_memory_updates,
        })
        return state

    async def _patch_persist_and_index(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        llm_client = self._get_step_llm_client(step_context)
        await self._patch_category_summaries(
            state.get("category_updates", {}),
            ctx=state["ctx"],
            store=state["store"],
            llm_client=llm_client,
        )
        return state

    def _patch_build_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        store = state["store"]
        item = self._model_dump_without_embeddings(state["memory_item"])
        category_updates_ids = list(state.get("category_updates", {}).keys())
        category_updates = [
            self._model_dump_without_embeddings(store.memory_category_repo.categories[c]) for c in category_updates_ids
        ]
        response = {
            "memory_item": item,
            "category_updates": category_updates,
        }
        state["response"] = response
        return state

    def _map_category_names_to_ids(self, names: list[str], ctx: Context) -> list[str]:
        if not names:
            return []
        mapped: list[str] = []
        seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            cid = ctx.category_name_to_id.get(key)
            if cid and cid not in seen:
                mapped.append(cid)
                seen.add(cid)
        return mapped

    async def _patch_category_summaries(
        self,
        updates: dict[str, list[str]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
    ) -> None:
        if not updates:
            return
        tasks = []
        target_ids: list[str] = []
        client = llm_client or self._get_llm_client()
        for cid, (content_before, content_after) in updates.items():
            cat = store.memory_category_repo.categories.get(cid)
            if not cat or (not content_before and not content_after):
                continue
            prompt = self._build_category_patch_prompt(
                category=cat, content_before=content_before, content_after=content_after
            )
            tasks.append(client.summarize(prompt, system_prompt=None))
            target_ids.append(cid)
        if not tasks:
            return
        patches = await asyncio.gather(*tasks)
        for cid, patch in zip(target_ids, patches, strict=True):
            need_update, summary = self._parse_category_patch_response(patch)
            if not need_update:
                continue
            cat = store.memory_category_repo.categories.get(cid)
            store.memory_category_repo.update_category(
                category_id=cid,
                summary=summary.strip(),
            )

    def _build_category_patch_prompt(
        self, *, category: MemoryCategory, content_before: str | None, content_after: str | None
    ) -> str:
        if content_before and content_after:
            update_content = "\n".join([
                "The memory content before:",
                content_before,
                "The memory content after:",
                content_after,
            ])
        elif content_before:
            update_content = "\n".join([
                "This memory content is discarded:",
                content_before,
            ])
        elif content_after:
            update_content = "\n".join([
                "This memory content is newly added:",
                content_after,
            ])
        original_content = category.summary or ""
        prompt = CATEGORY_PATCH_PROMPT
        return prompt.format(
            category=self._escape_prompt_value(category.name),
            original_content=self._escape_prompt_value(original_content or ""),
            update_content=self._escape_prompt_value(update_content or ""),
        )

    def _parse_category_patch_response(self, response: str) -> tuple[bool, str]:
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return False, ""
        if not isinstance(data, dict):
            return False, ""
        if not data.get("updated_content"):
            return False, ""
        need_update = data.get("need_update", False)
        updated_content = data["updated_content"].strip()
        if updated_content == "empty":
            updated_content = ""
        return need_update, updated_content
