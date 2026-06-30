from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any, cast, get_args

from pydantic import BaseModel

from memu.database.models import EntryType, RecallFile
from memu.prompts.category_patch import CATEGORY_PATCH_PROMPT
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import PatchConfig
    from memu.database.interfaces import Database


class CRUDMixin:
    if TYPE_CHECKING:
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_step_embedding_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]
        user_model: type[BaseModel]
        patch_config: PatchConfig
        _ensure_categories_ready: Callable[[Context, Database, Mapping[str, Any] | None], Awaitable[None]]

    async def list_recall_entries(
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

        result = await self._run_workflow("crud_list_recall_entries", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "List memory items workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def list_recall_files(
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
        result = await self._run_workflow("crud_list_recall_files", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "List memory categories workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def clear_memory(
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

        result = await self._run_workflow("crud_clear_memory", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Clear memory workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _build_list_recall_entries_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="list_recall_entries",
                role="read_memories",
                handler=self._crud_list_recall_entries,
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
    def _list_list_memories_initial_keys() -> set[str]:
        return {
            "ctx",
            "store",
            "where",
        }

    def _build_list_recall_files_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="list_recall_files",
                role="read_categories",
                handler=self._crud_list_recall_files,
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

    def _build_clear_memory_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="clear_memory_relations",
                role="delete_memories",
                handler=self._crud_clear_memory_relations,
                requires={"ctx", "store", "where"},
                produces={"deleted_relations"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="clear_recall_files",
                role="delete_memories",
                handler=self._crud_clear_recall_files,
                requires={"ctx", "store", "where"},
                produces={"deleted_categories"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="clear_recall_entries",
                role="delete_memories",
                handler=self._crud_clear_recall_entries,
                requires={"ctx", "store", "where"},
                produces={"deleted_items"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="clear_memory_resources",
                role="delete_memories",
                handler=self._crud_clear_memory_resources,
                requires={"ctx", "store", "where"},
                produces={"deleted_resources"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._crud_build_clear_memory_response,
                requires={
                    "ctx",
                    "store",
                    "deleted_relations",
                    "deleted_categories",
                    "deleted_items",
                    "deleted_resources",
                },
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_clear_memories_initial_keys() -> set[str]:
        return {
            "ctx",
            "store",
            "where",
        }

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

    def _crud_list_recall_entries(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        items = store.recall_entry_repo.list_items(where_filters)
        state["items"] = items
        return state

    def _crud_list_recall_files(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        # Lists memory-track files only; skill-track RecallFiles (ADR 0006) are excluded.
        categories = store.recall_file_repo.list_categories({**where_filters, "track": "memory"})
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

    def _crud_clear_memory_relations(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        deleted = store.recall_file_entry_repo.clear_relations(where_filters)
        state["deleted_relations"] = deleted
        return state

    def _crud_clear_recall_files(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        deleted = store.recall_file_repo.clear_categories(where_filters)
        state["deleted_categories"] = deleted
        return state

    def _crud_clear_recall_entries(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        deleted = store.recall_entry_repo.clear_items(where_filters)
        state["deleted_items"] = deleted
        return state

    def _crud_clear_memory_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        where_filters = state.get("where") or {}
        store = state["store"]
        deleted = store.resource_repo.clear_resources(where_filters)
        state["deleted_resources"] = deleted
        return state

    def _crud_build_clear_memory_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        deleted_categories = state.get("deleted_categories", {})
        deleted_items = state.get("deleted_items", {})
        deleted_resources = state.get("deleted_resources", {})
        deleted_relations = state.get("deleted_relations", [])
        response = {
            "deleted_categories": [self._model_dump_without_embeddings(cat) for cat in deleted_categories.values()],
            "deleted_items": [self._model_dump_without_embeddings(item) for item in deleted_items.values()],
            "deleted_resources": [self._model_dump_without_embeddings(res) for res in deleted_resources.values()],
            "deleted_relations": [rel.model_dump() for rel in deleted_relations],
        }
        state["response"] = response
        return state

    async def create_recall_entry(
        self,
        *,
        memory_type: EntryType,
        memory_content: str,
        recall_files: list[str],
        user: dict[str, Any] | None = None,
        propagate: bool = True,
    ) -> dict[str, Any]:
        if memory_type not in get_args(EntryType):
            msg = f"Invalid memory type: '{memory_type}', must be one of {get_args(EntryType)}"
            raise ValueError(msg)

        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        state: WorkflowState = {
            "memory_payload": {
                "type": memory_type,
                "content": memory_content,
                "categories": recall_files,
            },
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
            "propagate": propagate,
        }

        result = await self._run_workflow("patch_create", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Create memory item workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def update_recall_entry(
        self,
        *,
        memory_id: str,
        memory_type: EntryType | None = None,
        memory_content: str | None = None,
        recall_files: list[str] | None = None,
        user: dict[str, Any] | None = None,
        propagate: bool = True,
    ) -> dict[str, Any]:
        if all((memory_type is None, memory_content is None, recall_files is None)):
            msg = "At least one of memory type, memory content, or memory categories is required for UPDATE operation"
            raise ValueError(msg)
        if memory_type and memory_type not in get_args(EntryType):
            msg = f"Invalid memory type: '{memory_type}', must be one of {get_args(EntryType)}"
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
                "categories": recall_files,
            },
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
            "propagate": propagate,
        }

        result = await self._run_workflow("patch_update", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Update memory item workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def delete_recall_entry(
        self,
        *,
        memory_id: str,
        user: dict[str, Any] | None = None,
        propagate: bool = True,
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
            "propagate": propagate,
        }

        result = await self._run_workflow("patch_delete", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Delete memory item workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _build_create_recall_entry_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="create_recall_entry",
                role="patch",
                handler=self._patch_create_recall_entry,
                requires={"memory_payload", "ctx", "store", "user"},
                produces={"recall_entry", "category_updates"},
                capabilities={"db", "llm"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._patch_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
                config={"chat_llm_profile": "default"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._patch_build_response,
                requires={"recall_entry", "category_updates", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_create_recall_entry_initial_keys() -> set[str]:
        return {
            "memory_payload",
            "ctx",
            "store",
            "user",
        }

    def _build_update_recall_entry_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="update_recall_entry",
                role="patch",
                handler=self._patch_update_recall_entry,
                requires={"memory_id", "memory_payload", "ctx", "store", "user"},
                produces={"recall_entry", "category_updates"},
                capabilities={"db", "llm"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._patch_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
                config={"chat_llm_profile": "default"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._patch_build_response,
                requires={"recall_entry", "category_updates", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_update_recall_entry_initial_keys() -> set[str]:
        return {
            "memory_id",
            "memory_payload",
            "ctx",
            "store",
            "user",
        }

    def _build_delete_recall_entry_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="delete_recall_entry",
                role="patch",
                handler=self._patch_delete_recall_entry,
                requires={"memory_id", "ctx", "store", "user"},
                produces={"recall_entry", "category_updates"},
                capabilities={"db"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._patch_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
                config={"chat_llm_profile": "default"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._patch_build_response,
                requires={"recall_entry", "category_updates", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_delete_recall_entry_initial_keys() -> set[str]:
        return {
            "memory_id",
            "ctx",
            "store",
            "user",
        }

    async def _patch_create_recall_entry(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        memory_payload = state["memory_payload"]
        ctx = state["ctx"]
        store = state["store"]
        user = state["user"]
        propagate = state["propagate"]
        category_memory_updates: dict[str, tuple[Any, Any]] = {}

        embed_payload = [memory_payload["content"]]
        content_embedding = (await self._get_step_embedding_client(step_context).embed(embed_payload))[0]

        item = store.recall_entry_repo.create_item(
            memory_type=memory_payload["type"],
            summary=memory_payload["content"],
            embedding=content_embedding,
            user_data=dict(user or {}),
        )
        cat_names = memory_payload["categories"]
        mapped_cat_ids = self._map_category_names_to_ids(cat_names, ctx)
        for cid in mapped_cat_ids:
            store.recall_file_entry_repo.link_item_category(item.id, cid, user_data=dict(user or {}))
            if propagate:
                category_memory_updates[cid] = (None, memory_payload["content"])

        state.update({
            "recall_entry": item,
            "category_updates": category_memory_updates,
        })
        return state

    async def _patch_update_recall_entry(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        memory_id = state["memory_id"]
        memory_payload = state["memory_payload"]
        ctx = state["ctx"]
        store = state["store"]
        user = state["user"]
        propagate = state["propagate"]
        category_memory_updates: dict[str, tuple[Any, Any]] = {}

        item = store.recall_entry_repo.get_item(memory_id)
        if not item:
            msg = f"Memory item with id {memory_id} not found"
            raise ValueError(msg)
        old_content = item.summary
        old_item_categories = store.recall_file_entry_repo.get_item_categories(memory_id)
        mapped_old_cat_ids = [cat.category_id for cat in old_item_categories]

        if memory_payload["content"]:
            embed_payload = [memory_payload["content"]]
            content_embedding = (await self._get_step_embedding_client(step_context).embed(embed_payload))[0]
        else:
            content_embedding = None

        if memory_payload["type"] or memory_payload["content"]:
            item = store.recall_entry_repo.update_item(
                item_id=memory_id,
                memory_type=memory_payload["type"],
                summary=memory_payload["content"],
                embedding=content_embedding,
            )
        self._reconcile_update_categories(
            memory_id=memory_id,
            new_cat_names=memory_payload["categories"],
            mapped_old_cat_ids=mapped_old_cat_ids,
            content_changed=bool(memory_payload["content"]),
            old_content=old_content,
            new_summary=item.summary,
            ctx=ctx,
            store=store,
            user=user,
            propagate=propagate,
            category_memory_updates=category_memory_updates,
        )

        state.update({
            "recall_entry": item,
            "category_updates": category_memory_updates,
        })
        return state

    def _reconcile_update_categories(
        self,
        *,
        memory_id: str,
        new_cat_names: list[str] | None,
        mapped_old_cat_ids: list[str],
        content_changed: bool,
        old_content: Any,
        new_summary: Any,
        ctx: Any,
        store: Database,
        user: dict[str, Any] | None,
        propagate: bool,
        category_memory_updates: dict[str, tuple[Any, Any]],
    ) -> None:
        """Sync an item's category links for an UPDATE.

        ``new_cat_names is None`` means the caller omitted categories, so existing
        links are left untouched (an empty list, by contrast, clears all links).
        """
        if new_cat_names is None:
            if propagate and content_changed:
                for cid in mapped_old_cat_ids:
                    category_memory_updates[cid] = (old_content, new_summary)
            return

        mapped_new_cat_ids = self._map_category_names_to_ids(new_cat_names, ctx)
        old_set, new_set = set(mapped_old_cat_ids), set(mapped_new_cat_ids)
        for cid in old_set - new_set:
            store.recall_file_entry_repo.unlink_item_category(memory_id, cid)
            if propagate:
                category_memory_updates[cid] = (old_content, None)
        for cid in new_set - old_set:
            store.recall_file_entry_repo.link_item_category(memory_id, cid, user_data=dict(user or {}))
            if propagate:
                category_memory_updates[cid] = (None, new_summary)
        if propagate and content_changed:
            for cid in old_set & new_set:
                category_memory_updates[cid] = (old_content, new_summary)

    async def _patch_delete_recall_entry(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        memory_id = state["memory_id"]
        store = state["store"]
        propagate = state["propagate"]
        category_memory_updates: dict[str, tuple[Any, Any]] = {}

        item = store.recall_entry_repo.get_item(memory_id)
        if not item:
            msg = f"Memory item with id {memory_id} not found"
            raise ValueError(msg)
        item_categories = store.recall_file_entry_repo.get_item_categories(memory_id)
        if propagate:
            for cat in item_categories:
                category_memory_updates[cat.category_id] = (item.summary, None)
        # Remove the item's category relations first so deleting the item never
        # leaves orphan edges pointing at a non-existent item.
        store.recall_file_entry_repo.unlink_item(memory_id)
        store.recall_entry_repo.delete_item(memory_id)

        state.update({
            "recall_entry": item,
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
        item = self._model_dump_without_embeddings(state["recall_entry"])
        category_updates_ids = list(state.get("category_updates", {}).keys())
        category_updates = [
            self._model_dump_without_embeddings(store.recall_file_repo.categories[c]) for c in category_updates_ids
        ]
        response = {
            "recall_entry": item,
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
        updates: dict[str, tuple[str | None, str | None]],
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
            cat = store.recall_file_repo.categories.get(cid)
            if not cat or (not content_before and not content_after):
                continue
            prompt = self._build_category_patch_prompt(
                category=cat, content_before=content_before, content_after=content_after
            )
            tasks.append(client.chat(prompt))
            target_ids.append(cid)
        if not tasks:
            return
        patches = await asyncio.gather(*tasks)
        for cid, patch in zip(target_ids, patches, strict=True):
            need_update, summary = self._parse_category_patch_response(patch)
            if not need_update:
                continue
            cat = store.recall_file_repo.categories.get(cid)
            store.recall_file_repo.update_category(
                category_id=cid,
                content=summary.strip(),
            )

    def _build_category_patch_prompt(
        self, *, category: RecallFile, content_before: str | None, content_after: str | None
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
        original_content = category.content or ""
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
