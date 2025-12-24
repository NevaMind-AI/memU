
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Literal, Any, Callable, Awaitable, Mapping, cast, get_args

from pydantic import BaseModel

from memu.database.models import MemoryType, MemoryCategory, CategoryItem
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

    # create_memory_item
    # update_memory_item
    # delete_memory_item
    # list_memory_items - use where instead of user
    async def patch(
        self,
        operation: Literal["CREATE", "UPDATE", "DELETE"],
        *,
        memory_id: str | None = None,
        memory_type: MemoryType | None = None,
        memory_content: str | None = None,
        memory_categories: list[str] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_operation(operation, memory_id, memory_type, memory_content, memory_categories)

        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        state: WorkflowState = {
            "operation": operation,
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

        result = await self._run_workflow("patch", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Patch workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _validate_operation(
        self,
        operation: Literal["CREATE", "UPDATE", "DELETE"],
        memory_id: str | None = None,
        memory_type: MemoryType | None = None,
        memory_content: str | None = None,
        memory_categories: list[str] | None = None,
    ) -> None:
        if operation == "CREATE":
            if memory_type is None:
                raise ValueError("Memory type is required for CREATE operation")
            if memory_type not in get_args(MemoryType):
                raise ValueError(f"Invalid memory type: '{memory_type}', must be one of {get_args(MemoryType)}")
            if memory_content is None:
                raise ValueError("Memory content is required for CREATE operation")
            # Comment this if we allow orphan (not linked to any category) memory item
            # if memory_categories is None:
            #     raise ValueError("Memory categories are required for CREATE operation")
        elif operation == "UPDATE":
            if memory_id is None:
                raise ValueError("Memory ID is required for UPDATE operation")
            if all(
                (memory_type is None, memory_content is None, memory_categories is None)
            ):
                raise ValueError("At least one of memory type, memory content, or memory categories is required for UPDATE operation")
        elif operation == "DELETE":
            if memory_id is None:
                raise ValueError("Memory ID is required for DELETE operation")
        else:
            raise ValueError(f"Invalid operation: '{operation}', must be one of ['CREATE', 'UPDATE', 'DELETE']")

    def _build_patch_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="operate_memory_item",
                role="operate",
                handler=self._patch_operate_memory_item,
                requires={"operation", "memory_id", "memory_payload", "ctx", "store", "user"},
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
        
    def _patch_build_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        ctx = state["ctx"]
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

    async def _ensure_categories_ready(self, ctx: Context, store: Database, user_scope: Mapping[str, Any] | None = None) -> None:
        if ctx.categories_ready:
            return
        if ctx.category_init_task:
            await ctx.category_init_task
            ctx.category_init_task = None
            return
        await self._initialize_categories(ctx, store, user_scope)

    async def _initialize_categories(self, ctx: Context, store: Database, user: Mapping[str, Any] | None = None) -> None:
        if ctx.categories_ready:
            return
        if not self.category_configs:
            ctx.categories_ready = True
            return
        cat_texts = [self._category_embedding_text(cfg) for cfg in self.category_configs]
        cat_vecs = await self._get_llm_client().embed(cat_texts)
        ctx.category_ids = []
        ctx.category_name_to_id = {}
        for cfg, vec in zip(self.category_configs, cat_vecs, strict=True):
            name = (cfg.get("name") or "").strip() or "Untitled"
            description = (cfg.get("description") or "").strip()
            cat = store.memory_category_repo.get_or_create_category(
                name=name, description=description, embedding=vec, user_data=dict(user or {})
            )
            ctx.category_ids.append(cat.id)
            ctx.category_name_to_id[name.lower()] = cat.id
        ctx.categories_ready = True

    async def _patch_operate_memory_item(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        operation = state["operation"]
        memory_id = state["memory_id"]
        memory_payload = state["memory_payload"]
        ctx = state["ctx"]
        store = state["store"]
        user = state["user"]
        category_memory_updates: dict[str, [str, str]] = {}

        if memory_payload["content"]:
            embed_payload = [memory_payload["content"]]
            content_embedding = (await self._get_llm_client().embed(embed_payload))[0]
        else:
            content_embedding = None

        if operation == "CREATE":
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
        elif operation == "UPDATE":
            item = store.memory_item_repo.get_item(memory_id)
            if not item:
                raise ValueError(f"Memory item with id {memory_id} not found")
            old_content = item.summary
            old_item_categories = store.category_item_repo.get_item_categories(memory_id)
            mapped_old_cat_ids = [cat.category_id for cat in old_item_categories]

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
        elif operation == "DELETE":
            item = store.memory_item_repo.get_item(memory_id)
            if not item:
                raise ValueError(f"Memory item with id {memory_id} not found")
            item_categories = store.category_item_repo.get_item_categories  (memory_id)
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
            prompt = self._build_category_patch_prompt(category=cat, content_before=content_before, content_after=content_after)
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

    def _build_category_patch_prompt(self, *, category: MemoryCategory, content_before: str | None, content_after: str | None) -> str:
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
