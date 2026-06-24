from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import pathlib
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET
from pydantic import BaseModel

from memu.app.settings import CategoryConfig, CustomPrompt
from memu.blob.folder import diff_folder, load_manifest, manifest_from_scan, save_manifest, scan_folder
from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource
from memu.preprocess import PreprocessContext, preprocess_resource
from memu.prompts.category_summary import (
    CUSTOM_PROMPT as CATEGORY_SUMMARY_CUSTOM_PROMPT,
)
from memu.prompts.category_summary import (
    PROMPT as CATEGORY_SUMMARY_PROMPT,
)
from memu.prompts.memory_type import (
    CUSTOM_PROMPTS as MEMORY_TYPE_CUSTOM_PROMPTS,
)
from memu.prompts.memory_type import (
    CUSTOM_TYPE_CUSTOM_PROMPTS,
    DEFAULT_MEMORY_TYPES,
)
from memu.prompts.memory_type import (
    PROMPTS as MEMORY_TYPE_PROMPTS,
)
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import MemorizeConfig, MemoryFilesConfig
    from memu.blob.local_fs import LocalFS
    from memu.database.interfaces import Database


class MemorizeMixin:
    if TYPE_CHECKING:
        memorize_config: MemorizeConfig
        category_configs: list[CategoryConfig]
        category_config_map: dict[str, CategoryConfig]
        _category_prompt_str: str
        fs: LocalFS
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_step_embedding_client: Callable[[Mapping[str, Any] | None], Any]
        _get_embedding_client: Callable[..., Any]
        _get_llm_client: Callable[..., Any]
        _get_vlm_client: Callable[..., Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]
        user_model: type[BaseModel]

        # Memory file system export (provided by MemoryService).
        memory_files_config: MemoryFilesConfig
        _build_memory_files: Callable[..., Awaitable[dict[str, Any]]]

        # Provided by CRUDMixin (composed onto MemoryService).
        async def _patch_category_summaries(
            self,
            updates: dict[str, tuple[str | None, str | None]],
            ctx: Context,
            store: Database,
            llm_client: Any | None = None,
        ) -> None: ...

    async def memorize(
        self,
        *,
        resource_url: str,
        modality: str,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        memory_types = self._resolve_memory_types()

        state: WorkflowState = {
            "resource_url": resource_url,
            "modality": modality,
            "memory_types": memory_types,
            "categories_prompt_str": self._category_prompt_str,
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
        }

        result = await self._run_workflow("memorize", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Memorize workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    async def memorize_workspace(
        self,
        *,
        folder: str,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sync a folder of source files into memory by diffing an input manifest.

        Scans ``folder`` recursively, infers each file's modality by extension
        (unsupported extensions are skipped), and diffs against the sidecar
        ``.memu_manifest.json`` to find added/modified/deleted files. Modified and
        deleted files have their previously extracted memory cascade-deleted (with
        affected category summaries recomputed); added and modified files are
        (re)memorized by submitting each one through the single-file
        :meth:`memorize` workflow. The manifest is then rewritten.

        ``memorize`` itself is left untouched: this is purely an additive,
        directory-oriented entry point built on top of it.
        """
        ctx = self._get_context()
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        await self._ensure_categories_ready(ctx, store, user_scope)

        root = pathlib.Path(folder).resolve()
        scanned = scan_folder(root)
        manifest = load_manifest(root)
        diff = diff_folder(scanned, manifest)

        # 1. Cascade-delete memory for files that were modified or removed.
        stale_urls = {sf.abs_path for sf in diff.modified}
        stale_urls.update(str(root / rel) for rel in diff.deleted)
        removed_resources = await self._cascade_delete_by_urls(stale_urls, ctx=ctx, store=store, user_scope=user_scope)

        # 2. (Re)memorize added and modified files; each file maps to one Resource.
        changed_resources: list[Resource] = []
        items: list[dict[str, Any]] = []
        categories: list[dict[str, Any]] = []
        for scanned_file in [*diff.added, *diff.modified]:
            result = await self._memorize_one(
                resource_url=scanned_file.abs_path,
                modality=scanned_file.modality,
                user_scope=user_scope,
                ctx=ctx,
                store=store,
            )
            changed_resources.extend(cast("list[Resource]", result.get("resources") or []))
            response = cast("dict[str, Any]", result.get("response") or {})
            items.extend(response.get("items", []))
            # Categories reflect the cumulative scoped state, so the latest wins.
            if response.get("categories"):
                categories = response["categories"]

        # 3. Refresh the memory file tree (full rebuild when anything was removed).
        await self._update_memory_files(changed_resources, user_scope, force_full=diff.has_removals)

        # 4. Persist the updated input manifest.
        save_manifest(root, manifest_from_scan(scanned))

        return {
            "folder": str(root),
            "added": [sf.rel_path for sf in diff.added],
            "modified": [sf.rel_path for sf in diff.modified],
            "deleted": list(diff.deleted),
            "resources": [self._model_dump_without_embeddings(r) for r in changed_resources],
            "removed_resources": [self._model_dump_without_embeddings(r) for r in removed_resources],
            "items": items,
            "categories": categories,
        }

    async def _memorize_one(
        self,
        *,
        resource_url: str,
        modality: str,
        user_scope: dict[str, Any] | None,
        ctx: Context,
        store: Database,
    ) -> WorkflowState:
        """Run the memorize workflow for a single file (one file -> one Resource).

        This mirrors :meth:`memorize` but returns the full workflow state (so the
        workspace sync can collect the created resources) and takes an already
        resolved ``user_scope``/``ctx``/``store`` to avoid re-resolving them per file.
        """
        memory_types = self._resolve_memory_types()
        state: WorkflowState = {
            "resource_url": resource_url,
            "modality": modality,
            "memory_types": memory_types,
            "categories_prompt_str": self._category_prompt_str,
            "ctx": ctx,
            "store": store,
            "category_ids": list(ctx.category_ids),
            "user": user_scope,
        }
        result = await self._run_workflow("memorize", state)
        if result.get("response") is None:
            msg = "Memorize workflow failed to produce a response"
            raise RuntimeError(msg)
        return result

    async def _cascade_delete_by_urls(
        self,
        urls: set[str],
        *,
        ctx: Context,
        store: Database,
        user_scope: dict[str, Any] | None,
    ) -> list[Resource]:
        """Delete resources (and their items/relations) whose url is in ``urls``.

        Affected category summaries are recomputed so the structured memory stays
        consistent after a source file is changed or removed.
        """
        if not urls:
            return []
        where = user_scope or None
        targets = [res for res in store.resource_repo.list_resources(where=where).values() if res.url in urls]
        if not targets:
            return []
        target_ids = {res.id for res in targets}

        # Discarded item summaries per category, used to recompute summaries.
        category_discards: dict[str, list[str]] = {}
        for item in store.memory_item_repo.list_items(where=where).values():
            if item.resource_id not in target_ids:
                continue
            for relation in store.category_item_repo.get_item_categories(item.id):
                store.category_item_repo.unlink_item_category(item.id, relation.category_id)
                category_discards.setdefault(relation.category_id, []).append(item.summary)
            store.memory_item_repo.delete_item(item.id)

        for res in targets:
            store.resource_repo.delete_resource(res.id)

        updates: dict[str, tuple[str | None, str | None]] = {
            cid: ("\n".join(s for s in summaries if s and s.strip()), None)
            for cid, summaries in category_discards.items()
            if any(s and s.strip() for s in summaries)
        }
        if updates:
            await self._patch_category_summaries(updates, ctx=ctx, store=store, llm_client=self._get_llm_client())
        return targets

    async def _update_memory_files(
        self,
        changed_resources: list[Resource],
        user_scope: dict[str, Any] | None,
        *,
        force_full: bool = False,
    ) -> None:
        """Refresh the memory file tree after a workspace sync (init or incremental).

        Gated behind ``memory_files_config.enabled`` so a sync without the export
        feature configured is a no-op. When any file was modified or deleted
        (``force_full``), the tree is rebuilt from the full scoped store so stale
        skills/entries do not linger; otherwise an incremental update merges the
        just-created resources. Best-effort: the structured memory is already
        persisted, so an export error must not fail the sync.
        """
        if not getattr(self.memory_files_config, "enabled", False):
            return
        if not changed_resources and not force_full:
            return
        try:
            await self._build_memory_files(user_scope, changed=None if force_full else changed_resources)
        except Exception:
            logger.exception("Memory file export failed after workspace memorize")

    def _build_memorize_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="ingest_resource",
                role="ingest",
                handler=self._memorize_ingest_resource,
                requires={"resource_url", "modality"},
                produces={"local_path", "raw_text"},
                capabilities={"io"},
            ),
            WorkflowStep(
                step_id="preprocess_multimodal",
                role="preprocess",
                handler=self._memorize_preprocess_multimodal,
                requires={"local_path", "modality", "raw_text"},
                produces={"preprocessed_resources"},
                capabilities={"llm"},
                config={"chat_llm_profile": self.memorize_config.preprocess_llm_profile},
            ),
            WorkflowStep(
                step_id="extract_items",
                role="extract",
                handler=self._memorize_extract_items,
                requires={
                    "preprocessed_resources",
                    "memory_types",
                    "categories_prompt_str",
                    "modality",
                    "resource_url",
                },
                produces={"resource_plans"},
                capabilities={"llm"},
                config={"chat_llm_profile": self.memorize_config.memory_extract_llm_profile},
            ),
            WorkflowStep(
                step_id="dedupe_merge",
                role="dedupe_merge",
                handler=self._memorize_dedupe_merge,
                requires={"resource_plans"},
                produces={"resource_plans"},
                capabilities=set(),
            ),
            WorkflowStep(
                step_id="categorize_items",
                role="categorize",
                handler=self._memorize_categorize_items,
                requires={"resource_plans", "ctx", "store", "local_path", "modality", "user"},
                produces={"resources", "items", "relations", "category_updates"},
                capabilities={"db", "vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._memorize_persist_and_index,
                requires={"category_updates", "ctx", "store"},
                produces={"categories"},
                capabilities={"db", "llm"},
                config={"chat_llm_profile": self.memorize_config.category_update_llm_profile},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._memorize_build_response,
                requires={"resources", "items", "relations", "ctx", "store", "category_ids"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_memorize_initial_keys() -> set[str]:
        return {
            "resource_url",
            "modality",
            "memory_types",
            "categories_prompt_str",
            "ctx",
            "store",
            "category_ids",
            "user",
        }

    async def _memorize_ingest_resource(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        local_path, raw_text = await self.fs.fetch(state["resource_url"], state["modality"])
        state.update({"local_path": local_path, "raw_text": raw_text})
        return state

    # Modalities whose preprocessing analyzes media via the VLM (vision) client.
    _VISION_MODALITIES = frozenset({"image", "video"})

    async def _memorize_preprocess_multimodal(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        modality = state["modality"]
        client = self._get_step_llm_client(step_context)
        if modality in self._VISION_MODALITIES:
            with contextlib.suppress(KeyError):
                client = self._get_vlm_client(self.memorize_config.vlm_profile, step_context=step_context)
        preprocessed = await self._preprocess_resource_url(
            local_path=state["local_path"],
            text=state.get("raw_text"),
            modality=modality,
            llm_client=client,
        )
        if not preprocessed:
            preprocessed = [{"text": state.get("raw_text"), "caption": None}]
        state["preprocessed_resources"] = preprocessed
        return state

    async def _memorize_extract_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        llm_client = self._get_step_llm_client(step_context)
        preprocessed_resources = state.get("preprocessed_resources", [])
        resource_plans: list[dict[str, Any]] = []
        total_segments = len(preprocessed_resources) or 1

        for idx, prep in enumerate(preprocessed_resources):
            res_url = self._segment_resource_url(state["resource_url"], idx, total_segments)
            text = prep.get("text")
            caption = prep.get("caption")

            structured_entries = await self._generate_structured_entries(
                resource_url=res_url,
                modality=state["modality"],
                memory_types=state["memory_types"],
                text=text,
                categories_prompt_str=state["categories_prompt_str"],
                llm_client=llm_client,
            )

            resource_plans.append({
                "resource_url": res_url,
                "text": text,
                "caption": caption,
                "entries": structured_entries,
            })

        state["resource_plans"] = resource_plans
        return state

    def _memorize_dedupe_merge(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        # Placeholder for future dedup/merge logic
        state["resource_plans"] = state.get("resource_plans", [])
        return state

    async def _memorize_categorize_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        embed_client = self._get_step_embedding_client(step_context)
        ctx = state["ctx"]
        store = state["store"]
        modality = state["modality"]
        local_path = state["local_path"]
        resources: list[Resource] = []
        items: list[MemoryItem] = []
        relations: list[CategoryItem] = []
        category_updates: dict[str, list[tuple[str, str]]] = {}
        user_scope = state.get("user", {})

        for plan in state.get("resource_plans", []):
            res = await self._create_resource_with_caption(
                resource_url=plan["resource_url"],
                modality=modality,
                local_path=local_path,
                caption=plan.get("caption"),
                store=store,
                embed_client=embed_client,
                user=user_scope,
            )
            resources.append(res)

            entries = plan.get("entries") or []
            if not entries:
                continue

            mem_items, rels, cat_updates = await self._persist_memory_items(
                resource_id=res.id,
                structured_entries=entries,
                ctx=ctx,
                store=store,
                embed_client=embed_client,
                user=user_scope,
            )
            items.extend(mem_items)
            relations.extend(rels)
            for cat_id, mems in cat_updates.items():
                category_updates.setdefault(cat_id, []).extend(mems)

        state.update({
            "resources": resources,
            "items": items,
            "relations": relations,
            "category_updates": category_updates,
        })
        return state

    async def _memorize_persist_and_index(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        llm_client = self._get_step_llm_client(step_context)
        updated_summaries = await self._update_category_summaries(
            state.get("category_updates", {}),
            ctx=state["ctx"],
            store=state["store"],
            llm_client=llm_client,
        )
        if self.memorize_config.enable_item_references:
            await self._persist_item_references(
                updated_summaries=updated_summaries,
                category_updates=state.get("category_updates", {}),
                store=state["store"],
            )
        return state

    def _memorize_build_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        ctx = state["ctx"]
        store = state["store"]
        resources = [self._model_dump_without_embeddings(r) for r in state.get("resources", [])]
        items = [self._model_dump_without_embeddings(item) for item in state.get("items", [])]
        relations = [rel.model_dump() for rel in state.get("relations", [])]
        category_ids = state.get("category_ids") or list(ctx.category_ids)
        categories = [
            self._model_dump_without_embeddings(store.memory_category_repo.categories[c]) for c in category_ids
        ]

        if len(resources) == 1:
            response = {
                "resource": resources[0],
                "items": items,
                "categories": categories,
                "relations": relations,
            }
        else:
            response = {
                "resources": resources,
                "items": items,
                "categories": categories,
                "relations": relations,
            }
        state["response"] = response
        return state

    def _segment_resource_url(self, base_url: str, idx: int, total_segments: int) -> str:
        if total_segments <= 1:
            return base_url
        path = pathlib.Path(base_url)
        return f"{path.stem}_#segment_{idx}{path.suffix}"

    async def _fetch_and_preprocess_resource(
        self, resource_url: str, modality: str, llm_client: Any | None = None
    ) -> tuple[str, list[dict[str, str | None]]]:
        """
        Fetch and preprocess a resource.

        Returns:
            Tuple of (local_path, preprocessed_resources)
            where preprocessed_resources is a list of dicts with 'text' and 'caption'
        """
        local_path, text = await self.fs.fetch(resource_url, modality)
        preprocessed_resources = await self._preprocess_resource_url(
            local_path=local_path,
            text=text,
            modality=modality,
            llm_client=llm_client,
        )
        return local_path, preprocessed_resources

    async def _create_resource_with_caption(
        self,
        *,
        resource_url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        store: Database,
        embed_client: Any | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> Resource:
        caption_text = caption.strip() if caption else None
        if caption_text:
            client = embed_client or self._get_embedding_client()
            caption_embedding = (await client.embed([caption_text]))[0]
        else:
            caption_embedding = None

        res = store.resource_repo.create_resource(
            url=resource_url,
            modality=modality,
            local_path=local_path,
            caption=caption_text,
            embedding=caption_embedding,
            user_data=dict(user or {}),
        )
        # if caption:
        #     caption_text = caption.strip()
        #     if caption_text:
        #         res.caption = caption_text
        #         client = embed_client or self._get_llm_client()
        #         res.embedding = (await client.embed([caption_text]))[0]
        #         res.updated_at = pendulum.now()
        return res

    def _resolve_memory_types(self) -> list[MemoryType]:
        configured_types = self.memorize_config.memory_types or DEFAULT_MEMORY_TYPES
        return [cast(MemoryType, mtype) for mtype in configured_types]

    def _resolve_summary_prompt(self, modality: str, override: str | None) -> str | None:
        memo_settings = self.memorize_config
        result = memo_settings.multimodal_preprocess_prompts.get(modality)
        if override:
            return override
        if result is None:
            return (
                memo_settings.default_category_summary_prompt
                if isinstance(memo_settings.default_category_summary_prompt, str)
                else None
            )
        return result if isinstance(result, str) else None

    def _resolve_multimodal_preprocess_prompt(self, modality: str) -> str | None:
        memo_settings = self.memorize_config
        result = memo_settings.multimodal_preprocess_prompts.get(modality)
        return result if isinstance(result, str) else None

    @staticmethod
    def _resolve_custom_prompt(prompt: str | CustomPrompt, templates: Mapping[str, str]) -> str:
        if isinstance(prompt, str):
            return prompt
        valid_blocks = [
            (block.ordinal, name, block.prompt or templates.get(name))
            for name, block in prompt.items()
            if (block.ordinal >= 0 and (block.prompt or templates.get(name)))
        ]
        if not valid_blocks:
            # raise ValueError(f"No valid blocks contained in custom prompt: {prompt}")
            return ""
        sorted_blocks = sorted(valid_blocks)
        return "\n\n".join(block for (_, _, block) in sorted_blocks if block is not None)

    async def _generate_structured_entries(
        self,
        *,
        resource_url: str,
        modality: str,
        memory_types: list[MemoryType],
        text: str | None,
        categories_prompt_str: str,
        segments: list[dict[str, int | str]] | None = None,
        llm_client: Any | None = None,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        if not memory_types:
            return []

        client = llm_client or self._get_llm_client()
        if text:
            entries = await self._generate_text_entries(
                resource_text=text,
                modality=modality,
                memory_types=memory_types,
                categories_prompt_str=categories_prompt_str,
                segments=segments,
                llm_client=client,
            )
            return entries
            # if entries:
            #     return entries
            # no_result_entry = self._build_no_result_fallback(memory_types[0], resource_url, modality)
            # return [no_result_entry]

        return []
        # return self._build_no_text_fallback(memory_types, resource_url, modality)

    async def _generate_text_entries(
        self,
        *,
        resource_text: str,
        modality: str,
        memory_types: list[MemoryType],
        categories_prompt_str: str,
        segments: list[dict[str, int | str]] | None,
        llm_client: Any | None = None,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        if modality == "conversation" and segments:
            segment_entries = await self._generate_entries_for_segments(
                resource_text=resource_text,
                segments=segments,
                memory_types=memory_types,
                categories_prompt_str=categories_prompt_str,
                llm_client=llm_client,
            )
            if segment_entries:
                return segment_entries
        return await self._generate_entries_from_text(
            resource_text=resource_text,
            memory_types=memory_types,
            categories_prompt_str=categories_prompt_str,
            llm_client=llm_client,
        )

    async def _generate_entries_for_segments(
        self,
        *,
        resource_text: str,
        segments: list[dict[str, int | str]],
        memory_types: list[MemoryType],
        categories_prompt_str: str,
        llm_client: Any | None = None,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        entries: list[tuple[MemoryType, str, list[str]]] = []
        lines = resource_text.split("\n")
        max_idx = len(lines) - 1
        for segment in segments:
            start_idx = int(segment.get("start", 0))
            end_idx = int(segment.get("end", max_idx))
            segment_text = self._extract_segment_text(lines, start_idx, end_idx)
            if not segment_text:
                continue
            segment_entries = await self._generate_entries_from_text(
                resource_text=segment_text,
                memory_types=memory_types,
                categories_prompt_str=categories_prompt_str,
                llm_client=llm_client,
            )
            entries.extend(segment_entries)
        return entries

    async def _generate_entries_from_text(
        self,
        *,
        resource_text: str,
        memory_types: list[MemoryType],
        categories_prompt_str: str,
        llm_client: Any | None = None,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        if not memory_types:
            return []
        client = llm_client or self._get_llm_client()
        prompts = [
            self._build_memory_type_prompt(
                memory_type=mtype,
                resource_text=resource_text,
                categories_str=categories_prompt_str,
            )
            for mtype in memory_types
        ]
        valid_prompts = [prompt for prompt in prompts if prompt.strip()]
        # These prompts are instructions that request structured output, not text summaries.
        tasks = [client.chat(prompt_text) for prompt_text in valid_prompts]
        responses = await asyncio.gather(*tasks)
        return self._parse_structured_entries(memory_types, responses)

    def _parse_structured_entries(
        self, memory_types: list[MemoryType], responses: Sequence[str]
    ) -> list[tuple[MemoryType, str, list[str]]]:
        entries: list[tuple[MemoryType, str, list[str]]] = []
        for mtype, response in zip(memory_types, responses, strict=True):
            parsed = self._parse_memory_type_response_xml(response)
            # if not parsed:
            #     fallback_entry = response.strip()
            #     if fallback_entry:
            #         entries.append((mtype, fallback_entry, []))
            #     continue
            for entry in parsed:
                content = (entry.get("content") or "").strip()
                if not content:
                    continue
                cat_names = [c.strip() for c in entry.get("categories", []) if isinstance(c, str) and c.strip()]
                entries.append((mtype, content, cat_names))
        return entries

    def _extract_segment_text(self, lines: list[str], start_idx: int, end_idx: int) -> str | None:
        segment_lines = []
        for line in lines:
            match = re.match(r"\[(\d+)\]", line)
            if not match:
                continue
            idx = int(match.group(1))
            if start_idx <= idx <= end_idx:
                segment_lines.append(line)
        return "\n".join(segment_lines) if segment_lines else None

    def _build_no_text_fallback(
        self, memory_types: list[MemoryType], resource_url: str, modality: str
    ) -> list[tuple[MemoryType, str, list[str]]]:
        fallback = f"Resource {resource_url} ({modality}) stored. No text summary in v0."
        return [(mtype, f"{fallback} (memory type: {mtype}).", []) for mtype in memory_types]

    def _build_no_result_fallback(
        self, memory_type: MemoryType, resource_url: str, modality: str
    ) -> tuple[MemoryType, str, list[str]]:
        fallback = f"Resource {resource_url} ({modality}) stored. No structured memories generated."
        return memory_type, fallback, []

    async def _persist_memory_items(
        self,
        *,
        resource_id: str,
        structured_entries: list[tuple[MemoryType, str, list[str]]],
        ctx: Context,
        store: Database,
        embed_client: Any | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], list[CategoryItem], dict[str, list[tuple[str, str]]]]:
        """
        Persist memory items and track category updates.

        Returns:
            Tuple of (items, relations, category_updates)
            where category_updates maps category_id -> list of (item_id, summary) tuples
        """
        summary_payloads = [content for _, content, _ in structured_entries]
        client = embed_client or self._get_embedding_client()
        item_embeddings = await client.embed(summary_payloads) if summary_payloads else []
        items: list[MemoryItem] = []
        rels: list[CategoryItem] = []
        # Changed: now stores (item_id, summary) tuples for reference support
        category_memory_updates: dict[str, list[tuple[str, str]]] = {}

        reinforce = self.memorize_config.enable_item_reinforcement
        for (memory_type, summary_text, cat_names), emb in zip(structured_entries, item_embeddings, strict=True):
            item = store.memory_item_repo.create_item(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary_text,
                embedding=emb,
                user_data=dict(user or {}),
                reinforce=reinforce,
            )
            items.append(item)
            if reinforce and item.extra.get("reinforcement_count", 1) > 1:
                # existing item
                continue
            mapped_cat_ids = await self._resolve_category_ids(cat_names, ctx, store, user=user)
            for cid in mapped_cat_ids:
                rels.append(store.category_item_repo.link_item_category(item.id, cid, user_data=dict(user or {})))
                # Store (item_id, summary) tuple for reference support
                category_memory_updates.setdefault(cid, []).append((item.id, summary_text))

        return items, rels, category_memory_updates

    def _start_category_initialization(self, ctx: Context, store: Database) -> None:
        if ctx.categories_ready:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop:
            ctx.category_init_task = loop.create_task(self._initialize_categories(ctx, store))
        else:
            asyncio.run(self._initialize_categories(ctx, store))

    async def _ensure_categories_ready(
        self, ctx: Context, store: Database, user_scope: Mapping[str, Any] | None = None
    ) -> None:
        if ctx.categories_ready:
            return
        if ctx.category_init_task:
            await ctx.category_init_task
            ctx.category_init_task = None
            return
        await self._initialize_categories(ctx, store, user_scope)

    @staticmethod
    def _classify_categories(
        configs: list[CategoryConfig],
        existing_by_name: dict[str, MemoryCategory],
    ) -> tuple[
        list[tuple[int, CategoryConfig]],
        list[tuple[int, CategoryConfig, MemoryCategory]],
        dict[int, MemoryCategory],
    ]:
        to_create: list[tuple[int, CategoryConfig]] = []
        to_update: list[tuple[int, CategoryConfig, MemoryCategory]] = []
        ready: dict[int, MemoryCategory] = {}
        for i, cfg in enumerate(configs):
            name = cfg.name.strip() or "Untitled"
            description = cfg.description.strip()
            ex = existing_by_name.get(name)
            if ex is None:
                to_create.append((i, cfg))
            elif ex.embedding is None or (ex.description or "") != description:
                to_update.append((i, cfg, ex))
            else:
                ready[i] = ex
        return to_create, to_update, ready

    async def _initialize_categories(
        self, ctx: Context, store: Database, user: Mapping[str, Any] | None = None
    ) -> None:
        if ctx.categories_ready:
            return
        if not self.category_configs:
            ctx.categories_ready = True
            return

        user_data = dict(user or {})
        existing = store.memory_category_repo.list_categories(where=user_data or None)
        existing_by_name: dict[str, MemoryCategory] = {c.name: c for c in existing.values()}

        to_create, to_update, ready = self._classify_categories(self.category_configs, existing_by_name)

        needs_embed: list[tuple[int, CategoryConfig]] = []
        needs_embed.extend(to_create)
        needs_embed.extend((i, cfg) for i, cfg, _ in to_update)

        embed_map: dict[int, list[float]] = {}
        if needs_embed:
            texts = [self._category_embedding_text(cfg) for _, cfg in needs_embed]
            vecs = await self._get_embedding_client("embedding").embed(texts)
            for (i, _), vec in zip(needs_embed, vecs, strict=True):
                embed_map[i] = vec

        cats: dict[int, MemoryCategory] = dict(ready)

        for i, cfg in to_create:
            name = cfg.name.strip() or "Untitled"
            description = cfg.description.strip()
            cat = store.memory_category_repo.get_or_create_category(
                name=name, description=description, embedding=embed_map[i], user_data=user_data
            )
            cats[i] = cat

        for i, cfg, ex in to_update:
            description = cfg.description.strip()
            cat = store.memory_category_repo.update_category(
                category_id=ex.id, description=description, embedding=embed_map[i]
            )
            cats[i] = cat

        ctx.category_ids = []
        ctx.category_name_to_id = {}
        for i in range(len(self.category_configs)):
            cat = cats[i]
            ctx.category_ids.append(cat.id)
            name = self.category_configs[i].name.strip() or "Untitled"
            ctx.category_name_to_id[name.lower()] = cat.id
        ctx.categories_ready = True

    @staticmethod
    def _category_embedding_text(cat: CategoryConfig) -> str:
        name = cat.name.strip() or "Untitled"
        desc = cat.description.strip()
        return f"{name}: {desc}" if desc else name

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

    @staticmethod
    def _partition_category_names(names: list[str], ctx: Context) -> tuple[list[str], list[str]]:
        """Split proposed names into (known category ids, unknown names) with dedup."""
        known_ids: list[str] = []
        known_seen: set[str] = set()
        unknown: list[str] = []
        unknown_seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            if not key:
                continue
            cid = ctx.category_name_to_id.get(key)
            if cid is not None:
                if cid not in known_seen:
                    known_ids.append(cid)
                    known_seen.add(cid)
            elif key not in unknown_seen:
                unknown.append(name.strip())
                unknown_seen.add(key)
        return known_ids, unknown

    async def _resolve_category_ids(
        self,
        names: list[str],
        ctx: Context,
        store: Database,
        *,
        user: Mapping[str, Any] | None = None,
    ) -> list[str]:
        """Resolve extractor-proposed category names to ids, creating unknown ones.

        Implements the open/adaptive taxonomy: the kernel presets no categories, so any
        category name the extractor proposes is created on first sight and cached in the
        context. (Embedding-similarity merging of near-duplicate categories is handled
        later by consolidation; here we only do exact-name dedup.)
        """
        if not names:
            return []
        user_data = dict(user or {})
        resolved, unknown = self._partition_category_names(names, ctx)
        seen: set[str] = set(resolved)

        if unknown:
            vecs = await self._get_embedding_client("embedding").embed(unknown)
            for name, vec in zip(unknown, vecs, strict=True):
                cat = store.memory_category_repo.get_or_create_category(
                    name=name, description="", embedding=vec, user_data=user_data
                )
                ctx.category_name_to_id[name.lower()] = cat.id
                if cat.id not in ctx.category_ids:
                    ctx.category_ids.append(cat.id)
                if cat.id not in seen:
                    resolved.append(cat.id)
                    seen.add(cat.id)
        return resolved

    async def _preprocess_resource_url(
        self, *, local_path: str, text: str | None, modality: str, llm_client: Any | None = None
    ) -> list[dict[str, str | None]]:
        """Preprocess a resource by delegating to the per-format ``preprocess`` package.

        Returns a list of preprocessed resources, each with 'text' and 'caption'.
        """
        return await preprocess_resource(
            modality=modality,
            local_path=local_path,
            text=text,
            ctx=self._build_preprocess_context(),
            llm_client=llm_client,
        )

    def _build_preprocess_context(self) -> PreprocessContext:
        """Bundle the service dependencies the preprocessors need."""
        return PreprocessContext(
            get_llm_client=self._get_llm_client,
            get_vlm_client=lambda: self._get_vlm_client(self.memorize_config.vlm_profile),
            escape_prompt_value=self._escape_prompt_value,
            extract_json_blob=self._extract_json_blob,
            resolve_custom_prompt=self._resolve_custom_prompt,
            multimodal_preprocess_prompts=self.memorize_config.multimodal_preprocess_prompts,
        )

    def _format_categories_for_prompt(self, categories: list[CategoryConfig]) -> str:
        adaptive_hint = (
            "Assign each memory item 1-3 concise, reusable category names (short noun "
            "phrases). Reuse a listed category when one fits; otherwise propose a new "
            "concise category name. Categories are created automatically."
        )
        if not categories:
            return "No predefined categories yet.\n" + adaptive_hint
        lines = []
        for cat in categories:
            name = cat.name.strip() or "Untitled"
            desc = cat.description.strip()
            lines.append(f"- {name}: {desc}" if desc else f"- {name}")
        return "Existing categories (reuse when appropriate):\n" + "\n".join(lines) + "\n\n" + adaptive_hint

    def _add_conversation_indices(self, conversation: str) -> str:
        """
        Add [INDEX] markers to each line of the conversation.

        Args:
            conversation: Raw conversation text with lines

        Returns:
            Conversation with [INDEX] markers prepended to each non-empty line
        """
        lines = conversation.split("\n")
        indexed_lines = []
        index = 0

        for line in lines:
            stripped = line.strip()
            if stripped:  # Only index non-empty lines
                indexed_lines.append(f"[{index}] {line}")
                index += 1
            else:
                # Preserve empty lines without indexing
                indexed_lines.append(line)

        return "\n".join(indexed_lines)

    def _build_memory_type_prompt(self, *, memory_type: MemoryType, resource_text: str, categories_str: str) -> str:
        configured_prompt = self.memorize_config.memory_type_prompts.get(memory_type)
        if configured_prompt is None:
            template = MEMORY_TYPE_PROMPTS.get(memory_type)
        elif isinstance(configured_prompt, str):
            template = configured_prompt
        else:
            template = self._resolve_custom_prompt(
                configured_prompt, MEMORY_TYPE_CUSTOM_PROMPTS.get(memory_type, CUSTOM_TYPE_CUSTOM_PROMPTS)
            )
        if not template:
            return resource_text
        safe_resource = self._escape_prompt_value(resource_text)
        safe_categories = self._escape_prompt_value(categories_str)
        return template.format(resource=safe_resource, categories_str=safe_categories)

    def _build_item_ref_id(self, item_id: str) -> str:
        return item_id.replace("-", "")[:6]

    def _extract_refs_from_summaries(self, summaries: dict[str, str]) -> set[str]:
        """
        Extract all [ref:xxx] references from summary texts.

        Args:
            summaries: dict mapping category_id -> summary text

        Returns:
            Set of all referenced short IDs (the xxx part from [ref:xxx])
        """
        from memu.utils.references import extract_references

        refs: set[str] = set()
        for summary in summaries.values():
            refs.update(extract_references(summary))
        return refs

    async def _persist_item_references(
        self,
        *,
        updated_summaries: dict[str, str],
        category_updates: dict[str, list[tuple[str, str]]],
        store: Database,
    ) -> None:
        """
        Persist ref_id to items that are referenced in category summaries.

        This function:
        1. Extracts all [ref:xxx] patterns from updated summaries
        2. Builds a mapping of short_id -> full item_id for all items in category_updates
        3. For items whose short_id appears in the references, updates their extra column
           with {"ref_id": short_id}
        """
        # Extract all referenced short IDs from summaries
        referenced_short_ids = self._extract_refs_from_summaries(updated_summaries)
        if not referenced_short_ids:
            return

        # Build mapping of short_id -> full item_id for all items in category_updates
        short_id_to_item_id: dict[str, str] = {}
        for item_tuples in category_updates.values():
            for item_id, _ in item_tuples:
                short_id = self._build_item_ref_id(item_id)
                short_id_to_item_id[short_id] = item_id

        # Update extra column for referenced items
        for short_id in referenced_short_ids:
            matched_item_id = short_id_to_item_id.get(short_id)
            if matched_item_id:
                store.memory_item_repo.update_item(
                    item_id=matched_item_id,
                    extra={"ref_id": short_id},
                )

    def _build_category_summary_prompt(
        self,
        *,
        category: MemoryCategory,
        new_memories: list[str] | list[tuple[str, str]],
    ) -> str:
        """
        Build the prompt for updating a category summary.

        Args:
            category: The category to update
            new_memories: Either list of summary strings (legacy) or list of (item_id, summary) tuples (with refs)
        """
        # Check if references are enabled and we have (id, summary) tuples
        enable_refs = getattr(self.memorize_config, "enable_item_references", False)

        if enable_refs:
            from memu.prompts.category_summary import (
                CUSTOM_PROMPT_WITH_REFS as category_summary_custom_prompt,
            )
            from memu.prompts.category_summary import (
                PROMPT_WITH_REFS as category_summary_prompt,
            )

            tuple_memories = cast(list[tuple[str, str]], new_memories)
            new_items_text = "\n".join(
                f"- [{self._build_item_ref_id(item_id)}] {summary}"
                for item_id, summary in tuple_memories
                if summary.strip()
            )
        else:
            category_summary_prompt = CATEGORY_SUMMARY_PROMPT
            category_summary_custom_prompt = CATEGORY_SUMMARY_CUSTOM_PROMPT

            if new_memories and isinstance(new_memories[0], tuple):
                tuple_memories = cast(list[tuple[str, str]], new_memories)
                new_items_text = "\n".join(f"- {summary}" for item_id, summary in tuple_memories if summary.strip())
            else:
                str_memories = cast(list[str], new_memories)
                new_items_text = "\n".join(f"- {m}" for m in str_memories if m.strip())

        original = category.summary or ""
        category_config = self.category_config_map.get(category.name)
        configured_prompt = (
            category_config and category_config.summary_prompt
        ) or self.memorize_config.default_category_summary_prompt
        if configured_prompt is None:
            prompt = category_summary_prompt
        elif isinstance(configured_prompt, str):
            prompt = configured_prompt
        else:
            prompt = self._resolve_custom_prompt(configured_prompt, category_summary_custom_prompt)
        target_length = (
            category_config and category_config.target_length
        ) or self.memorize_config.default_category_summary_target_length
        return prompt.format(
            category=self._escape_prompt_value(category.name),
            original_content=self._escape_prompt_value(original or ""),
            new_memory_items_text=self._escape_prompt_value(new_items_text or "No new memory items."),
            target_length=target_length,
        )

    async def _update_category_summaries(
        self,
        updates: dict[str, list[tuple[str, str]]] | dict[str, list[str]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
    ) -> dict[str, str]:
        """
        Update category summaries based on new memory items.

        Returns:
            dict mapping category_id -> updated summary text
        """
        updated_summaries: dict[str, str] = {}
        if not updates:
            return updated_summaries
        tasks = []
        target_ids: list[str] = []
        client = llm_client or self._get_llm_client()
        for cid, memories in updates.items():
            cat = store.memory_category_repo.categories.get(cid)
            if not cat or not memories:
                continue
            prompt = self._build_category_summary_prompt(category=cat, new_memories=memories)
            tasks.append(client.chat(prompt))
            target_ids.append(cid)
        if not tasks:
            return updated_summaries
        summaries = await asyncio.gather(*tasks)
        for cid, summary in zip(target_ids, summaries, strict=True):
            cat = store.memory_category_repo.categories.get(cid)
            if not cat:
                continue
            cleaned_summary = summary.replace("```markdown", "").replace("```", "").strip()
            store.memory_category_repo.update_category(
                category_id=cid,
                summary=cleaned_summary,
            )
            updated_summaries[cid] = cleaned_summary
        return updated_summaries

    def _parse_conversation_preprocess(self, raw: str) -> tuple[str | None, str | None]:
        conversation = self._extract_tag_content(raw, "conversation")
        summary = self._extract_tag_content(raw, "summary")
        return conversation, summary

    @staticmethod
    def _extract_tag_content(raw: str, tag: str) -> str | None:
        pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.IGNORECASE | re.DOTALL)
        match = pattern.search(raw)
        if not match:
            return None
        content = match.group(1).strip()
        return content or None

    def _parse_memory_type_response(self, raw: str) -> list[dict[str, Any]]:
        if not raw:
            return []
        raw = raw.strip()
        if not raw:
            return []
        payload = None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            try:
                blob = self._extract_json_blob(raw)
                payload = json.loads(blob)
            except Exception:
                return []
        if not isinstance(payload, dict):
            return []
        items = payload.get("memories_items")
        if not isinstance(items, list):
            return []
        normalized: list[dict[str, Any]] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            normalized.append(entry)
        return normalized

    def _find_xml_boundaries(self, raw: str) -> tuple[int, int, str] | None:
        """Find the start index, end index, and closing tag for XML root element."""
        root_tags = ["item", "profile", "behaviors", "events", "knowledge", "skills"]
        for tag in root_tags:
            opening = f"<{tag}>"
            closing = f"</{tag}>"
            start_idx = raw.find(opening)
            if start_idx != -1:
                end_idx = raw.rfind(closing)
                if end_idx != -1:
                    return (start_idx, end_idx, closing)
        return None

    def _parse_memory_element(self, memory_elem: Element) -> dict[str, Any] | None:
        """Parse a single memory XML element into a dict."""
        memory_dict: dict[str, Any] = {}

        content_elem = memory_elem.find("content")
        if content_elem is not None and content_elem.text:
            memory_dict["content"] = content_elem.text.strip()

        categories_elem = memory_elem.find("categories")
        if categories_elem is not None:
            categories = [cat_elem.text.strip() for cat_elem in categories_elem.findall("category") if cat_elem.text]
            memory_dict["categories"] = categories

        if memory_dict.get("content") and memory_dict.get("categories"):
            return memory_dict
        return None

    def _parse_memory_type_response_xml(self, raw: str) -> list[dict[str, Any]]:
        """
        Parse XML memory extraction output into a list of memory items.

        Expected XML format (root tag varies by memory type):
        <profile|behaviors|events|knowledge|skills>
            <memory>
                <content>...</content>
                <categories>
                    <category>...</category>
                </categories>
            </memory>
        </...>
        """
        if not raw or not raw.strip():
            return []
        raw = raw.strip()

        try:
            boundaries = self._find_xml_boundaries(raw)
            if boundaries is None:
                logger.warning("Could not find valid root tag in XML response")
                return []

            start_idx, end_idx, end_tag = boundaries
            xml_content = raw[start_idx : end_idx + len(end_tag)]
            xml_content = xml_content.replace("&", "&amp;")

            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                # Some LLMs emit one <item> per memory rather than a single root
                # element wrapping all memories, resulting in "junk after document
                # element" when the slice contains multiple top-level tags.  Wrap
                # the content in a synthetic root element and retry.
                root = ET.fromstring(f"<_root_>{xml_content}</_root_>")

            result: list[dict[str, Any]] = []

            for memory_elem in root.iter("memory"):
                parsed = self._parse_memory_element(memory_elem)
                if parsed:
                    result.append(parsed)

        except ET.ParseError:
            logger.exception("Failed to parse XML")
            return []
        else:
            return result
