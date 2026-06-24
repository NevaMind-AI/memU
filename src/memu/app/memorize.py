from __future__ import annotations

import asyncio
import contextlib
import logging
import pathlib
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET
from pydantic import BaseModel

from memu.app.settings import CategoryConfig, CustomPrompt, LaneConfig
from memu.blob.folder import diff_folder, load_manifest, manifest_from_scan, save_manifest, scan_folder
from memu.database.models import Entry, EntryType, Resource, ResourceEntry
from memu.memory_fs.exporter import slugify
from memu.preprocess import PreprocessContext, preprocess_resource
from memu.prompts.category_summary import (
    CUSTOM_PROMPT as CATEGORY_SUMMARY_CUSTOM_PROMPT,
)
from memu.prompts.category_summary import (
    PROMPT as CATEGORY_SUMMARY_PROMPT,
)
from memu.prompts.entry_type import (
    CUSTOM_PROMPTS as ENTRY_TYPE_CUSTOM_PROMPTS,
)
from memu.prompts.entry_type import (
    CUSTOM_TYPE_CUSTOM_PROMPTS,
)
from memu.prompts.entry_type import (
    PROMPTS as ENTRY_TYPE_PROMPTS,
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
        lane_configs: dict[str, LaneConfig]
        lane_category_config_maps: dict[str, dict[str, CategoryConfig]]
        lane_prompt_strs: dict[str, str]
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
        await self._ensure_lanes_ready(ctx, store, user_scope)

        state: WorkflowState = {
            "resource_url": resource_url,
            "modality": modality,
            "ctx": ctx,
            "store": store,
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
        await self._ensure_lanes_ready(ctx, store, user_scope)

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
        state: WorkflowState = {
            "resource_url": resource_url,
            "modality": modality,
            "ctx": ctx,
            "store": store,
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
        for item in store.entry_repo.list_entries(where=where).values():
            if item.source_id not in target_ids:
                continue
            for relation in store.resource_entry_repo.get_entry_resources(item.id):
                store.resource_entry_repo.unlink_entry_resource(item.id, relation.resource_id)
                category_discards.setdefault(relation.resource_id, []).append(item.text)
            store.entry_repo.delete_entry(item.id)

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
                    "modality",
                    "resource_url",
                },
                produces={"resource_plans"},
                capabilities={"llm"},
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
                produces={"resources", "items", "relations", "lane_updates"},
                capabilities={"db", "vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="persist_index",
                role="persist",
                handler=self._memorize_persist_and_index,
                requires={"lane_updates", "ctx", "store"},
                produces={"lane_docs"},
                capabilities={"db", "llm"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="emit",
                handler=self._memorize_build_response,
                requires={"resources", "items", "relations", "lane_updates", "ctx", "store"},
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
            "ctx",
            "store",
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
        preprocessed_resources = state.get("preprocessed_resources", [])
        resource_plans: list[dict[str, Any]] = []
        total_segments = len(preprocessed_resources) or 1
        enabled_lanes = self.memorize_config.enabled_lanes

        for idx, prep in enumerate(preprocessed_resources):
            res_url = self._segment_resource_url(state["resource_url"], idx, total_segments)
            text = prep.get("text")
            caption = prep.get("caption")

            lane_entries: dict[str, list[tuple[EntryType, str, list[str]]]] = {}
            for lane, lane_cfg in enabled_lanes.items():
                lane_client = self._get_llm_client(lane_cfg.extract_llm_profile, step_context=step_context)
                lane_entries[lane] = await self._generate_structured_entries(
                    modality=state["modality"],
                    lane=lane,
                    lane_cfg=lane_cfg,
                    text=text,
                    categories_prompt_str=self.lane_prompt_strs.get(lane, ""),
                    llm_client=lane_client,
                )

            resource_plans.append({
                "resource_url": res_url,
                "text": text,
                "caption": caption,
                "lane_entries": lane_entries,
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
        items: list[Entry] = []
        relations: list[ResourceEntry] = []
        # lane -> {doc_id: [(entry_id, text)]}
        lane_updates: dict[str, dict[str, list[tuple[str, str]]]] = {}
        user_scope = state.get("user", {})
        enabled_lanes = self.memorize_config.enabled_lanes

        for plan in state.get("resource_plans", []):
            res = await self._create_resource_with_caption(
                resource_url=plan["resource_url"],
                modality=modality,
                local_path=local_path,
                caption=plan.get("caption"),
                content=plan.get("text"),
                store=store,
                embed_client=embed_client,
                user=user_scope,
            )
            resources.append(res)

            plan_lane_entries = plan.get("lane_entries") or {}
            for lane, lane_cfg in enabled_lanes.items():
                entries = plan_lane_entries.get(lane) or []
                if not entries:
                    continue
                mem_items, rels, doc_updates = await self._persist_lane_entries(
                    lane=lane,
                    lane_cfg=lane_cfg,
                    source_resource=res,
                    structured_entries=entries,
                    ctx=ctx,
                    store=store,
                    embed_client=embed_client,
                    user=user_scope,
                )
                items.extend(mem_items)
                relations.extend(rels)
                lane_bucket = lane_updates.setdefault(lane, {})
                for doc_id, mems in doc_updates.items():
                    lane_bucket.setdefault(doc_id, []).extend(mems)

        state.update({
            "resources": resources,
            "items": items,
            "relations": relations,
            "lane_updates": lane_updates,
        })
        return state

    async def _memorize_persist_and_index(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        ctx = state["ctx"]
        store = state["store"]
        lane_updates: dict[str, dict[str, list[tuple[str, str]]]] = state.get("lane_updates", {})
        for lane, lane_cfg in self.memorize_config.enabled_lanes.items():
            # Only adaptive lanes synthesize a group-doc summary; per_resource lanes
            # already finalized their 1:1 doc summary during persistence.
            if lane_cfg.grouping != "adaptive":
                continue
            updates = lane_updates.get(lane) or {}
            if not updates:
                continue
            llm_client = self._get_llm_client(lane_cfg.summary_llm_profile, step_context=step_context)
            updated_summaries = await self._update_group_summaries(
                lane,
                lane_cfg,
                updates,
                ctx=ctx,
                store=store,
                llm_client=llm_client,
            )
            if lane_cfg.enable_item_references:
                await self._persist_item_references(
                    updated_summaries=updated_summaries,
                    category_updates=updates,
                    store=store,
                )
        state["lane_docs"] = lane_updates
        return state

    def _memorize_build_response(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        store = state["store"]
        resources = [self._model_dump_without_embeddings(r) for r in state.get("resources", [])]
        items = [self._model_dump_without_embeddings(item) for item in state.get("items", [])]
        relations = [rel.model_dump() for rel in state.get("relations", [])]

        # Per-lane coarse docs touched by this memorize, keyed by lane.
        lane_updates: dict[str, dict[str, list[tuple[str, str]]]] = state.get("lane_updates", {})
        lane_docs: dict[str, list[dict[str, Any]]] = {}
        for lane, doc_map in lane_updates.items():
            lane_docs[lane] = [
                self._model_dump_without_embeddings(res)
                for did in doc_map
                if (res := store.resource_repo.get_resource(did)) is not None
            ]
        # Backward-friendly alias: "categories" continues to mean the memory lane docs.
        categories = lane_docs.get("memory", [])

        response: dict[str, Any] = {
            "items": items,
            "categories": categories,
            "lanes": lane_docs,
            "relations": relations,
        }
        if len(resources) == 1:
            response["resource"] = resources[0]
        else:
            response["resources"] = resources
        state["response"] = response
        return state

    def _segment_resource_url(self, base_url: str, idx: int, total_segments: int) -> str:
        if total_segments <= 1:
            return base_url
        path = pathlib.Path(base_url)
        return f"{path.stem}_#segment_{idx}{path.suffix}"

    async def _create_resource_with_caption(
        self,
        *,
        resource_url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        content: str | None = None,
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

        return store.resource_repo.create_resource(
            lane="source",
            url=resource_url,
            modality=modality,
            local_path=local_path,
            content=content,
            summary=caption_text,
            embedding=caption_embedding,
            user_data=dict(user or {}),
        )

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
        modality: str,
        lane: str,
        lane_cfg: LaneConfig,
        text: str | None,
        categories_prompt_str: str,
        segments: list[dict[str, int | str]] | None = None,
        llm_client: Any | None = None,
    ) -> list[tuple[EntryType, str, list[str]]]:
        entry_types = [cast(EntryType, mtype) for mtype in lane_cfg.entry_types]
        if not entry_types or not text:
            return []

        client = llm_client or self._get_llm_client()
        return await self._generate_text_entries(
            resource_text=text,
            modality=modality,
            lane=lane,
            lane_cfg=lane_cfg,
            entry_types=entry_types,
            categories_prompt_str=categories_prompt_str,
            segments=segments,
            llm_client=client,
        )

    async def _generate_text_entries(
        self,
        *,
        resource_text: str,
        modality: str,
        lane: str,
        lane_cfg: LaneConfig,
        entry_types: list[EntryType],
        categories_prompt_str: str,
        segments: list[dict[str, int | str]] | None,
        llm_client: Any | None = None,
    ) -> list[tuple[EntryType, str, list[str]]]:
        if modality == "conversation" and segments:
            segment_entries = await self._generate_entries_for_segments(
                resource_text=resource_text,
                segments=segments,
                lane=lane,
                lane_cfg=lane_cfg,
                entry_types=entry_types,
                categories_prompt_str=categories_prompt_str,
                llm_client=llm_client,
            )
            if segment_entries:
                return segment_entries
        return await self._generate_entries_from_text(
            resource_text=resource_text,
            lane=lane,
            lane_cfg=lane_cfg,
            entry_types=entry_types,
            categories_prompt_str=categories_prompt_str,
            llm_client=llm_client,
        )

    async def _generate_entries_for_segments(
        self,
        *,
        resource_text: str,
        segments: list[dict[str, int | str]],
        lane: str,
        lane_cfg: LaneConfig,
        entry_types: list[EntryType],
        categories_prompt_str: str,
        llm_client: Any | None = None,
    ) -> list[tuple[EntryType, str, list[str]]]:
        entries: list[tuple[EntryType, str, list[str]]] = []
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
                lane=lane,
                lane_cfg=lane_cfg,
                entry_types=entry_types,
                categories_prompt_str=categories_prompt_str,
                llm_client=llm_client,
            )
            entries.extend(segment_entries)
        return entries

    async def _generate_entries_from_text(
        self,
        *,
        resource_text: str,
        lane: str,
        lane_cfg: LaneConfig,
        entry_types: list[EntryType],
        categories_prompt_str: str,
        llm_client: Any | None = None,
    ) -> list[tuple[EntryType, str, list[str]]]:
        if not entry_types:
            return []
        client = llm_client or self._get_llm_client()
        prompts = [
            self._build_entry_type_prompt(
                entry_type=mtype,
                lane_cfg=lane_cfg,
                resource_text=resource_text,
                categories_str=categories_prompt_str,
            )
            for mtype in entry_types
        ]
        valid_prompts = [prompt for prompt in prompts if prompt.strip()]
        # These prompts are instructions that request structured output, not text summaries.
        tasks = [client.chat(prompt_text) for prompt_text in valid_prompts]
        responses = await asyncio.gather(*tasks)
        return self._parse_structured_entries(entry_types, responses)

    def _parse_structured_entries(
        self, entry_types: list[EntryType], responses: Sequence[str]
    ) -> list[tuple[EntryType, str, list[str]]]:
        entries: list[tuple[EntryType, str, list[str]]] = []
        for mtype, response in zip(entry_types, responses, strict=True):
            parsed = self._parse_entry_type_response_xml(response)
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

    async def _persist_lane_entries(
        self,
        *,
        lane: str,
        lane_cfg: LaneConfig,
        source_resource: Resource,
        structured_entries: list[tuple[EntryType, str, list[str]]],
        ctx: Context,
        store: Database,
        embed_client: Any | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> tuple[list[Entry], list[ResourceEntry], dict[str, list[tuple[str, str]]]]:
        """Persist a lane's entries and track its coarse-doc updates.

        Returns ``(entries, relations, doc_updates)`` where ``doc_updates`` maps a
        coarse lane-doc id -> list of ``(entry_id, text)`` tuples. Grouping depends
        on ``lane_cfg.grouping``: ``adaptive`` resolves extractor-proposed group
        names to lane docs (creating unseen ones), while ``per_resource`` links all
        of a source's entries to a single 1:1 lane doc.
        """
        summary_payloads = [content for _, content, _ in structured_entries]
        client = embed_client or self._get_embedding_client()
        item_embeddings = await client.embed(summary_payloads) if summary_payloads else []
        items: list[Entry] = []
        rels: list[ResourceEntry] = []
        # Stores (entry_id, text) tuples for reference support.
        doc_updates: dict[str, list[tuple[str, str]]] = {}

        per_resource = lane_cfg.grouping == "per_resource"
        per_resource_doc_id = (
            self._ensure_per_resource_doc(lane, source_resource, store, user=user) if per_resource else None
        )

        reinforce = lane_cfg.enable_item_reinforcement
        for (entry_type, summary_text, cat_names), emb in zip(structured_entries, item_embeddings, strict=True):
            item = store.entry_repo.create_entry(
                lane=lane,
                source_id=source_resource.id,
                source_path=source_resource.source_path,
                entry_type=entry_type,
                text=summary_text,
                embedding=emb,
                user_data=dict(user or {}),
                reinforce=reinforce,
            )
            items.append(item)
            if reinforce and item.extra.get("reinforcement_count", 1) > 1:
                # existing item
                continue
            if per_resource:
                doc_ids = [per_resource_doc_id] if per_resource_doc_id else []
            else:
                doc_ids = await self._resolve_group_ids(lane, cat_names, ctx, store, user=user)
            for did in doc_ids:
                rels.append(store.resource_entry_repo.link_entry_resource(item.id, did, user_data=dict(user or {})))
                # Store (entry_id, text) tuple for reference support
                doc_updates.setdefault(did, []).append((item.id, summary_text))

        if per_resource and per_resource_doc_id and items:
            # A per_resource (index) doc has no LLM summary synthesis: its searchable
            # body is just the concatenation of its description entries.
            body = "\n".join(item.text for item in items if (item.text or "").strip())
            store.resource_repo.update_resource(
                resource_id=per_resource_doc_id,
                summary=body,
                embedding=item_embeddings[0] if item_embeddings else None,
            )

        return items, rels, doc_updates

    def _ensure_per_resource_doc(
        self,
        lane: str,
        source_resource: Resource,
        store: Database,
        *,
        user: Mapping[str, Any] | None = None,
    ) -> str:
        """Get-or-create the single coarse lane doc that 1:1 mirrors a source.

        Used by ``per_resource`` lanes (e.g. index): the doc is keyed by the source
        resource id so re-memorizing the same source reuses it. Returns the doc id.
        """
        from os.path import basename

        name = basename(source_resource.url or source_resource.local_path or source_resource.id)
        title = name or source_resource.id
        slug = f"{slugify(title)}-{source_resource.id[:8]}"
        doc = store.resource_repo.get_or_create_doc(
            lane=lane,
            title=title,
            description=source_resource.summary or "",
            embedding=source_resource.embedding or [],
            user_data=dict(user or {}),
            slug=slug,
        )
        return doc.id

    async def _ensure_lanes_ready(
        self, ctx: Context, store: Database, user_scope: Mapping[str, Any] | None = None
    ) -> None:
        """Initialize seed group docs for every enabled adaptive lane (idempotent)."""
        for lane, lane_cfg in self.memorize_config.enabled_lanes.items():
            lane_state = ctx.lane(lane)
            if lane_cfg.grouping != "adaptive":
                lane_state.ready = True
                continue
            if lane_state.ready:
                continue
            await self._initialize_lane_groups(lane, lane_cfg, ctx, store, user_scope)

    @staticmethod
    def _classify_categories(
        configs: list[CategoryConfig],
        existing_by_name: dict[str, Resource],
    ) -> tuple[
        list[tuple[int, CategoryConfig]],
        list[tuple[int, CategoryConfig, Resource]],
        dict[int, Resource],
    ]:
        to_create: list[tuple[int, CategoryConfig]] = []
        to_update: list[tuple[int, CategoryConfig, Resource]] = []
        ready: dict[int, Resource] = {}
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

    async def _initialize_lane_groups(
        self, lane: str, lane_cfg: LaneConfig, ctx: Context, store: Database, user: Mapping[str, Any] | None = None
    ) -> None:
        lane_state = ctx.lane(lane)
        if lane_state.ready:
            return
        seeds = lane_cfg.seed_categories
        if not seeds:
            lane_state.ready = True
            return

        user_data = dict(user or {})
        existing = store.resource_repo.list_resources(where=user_data or None, lane=lane)
        existing_by_name: dict[str, Resource] = {c.title: c for c in existing.values() if c.title}

        to_create, to_update, ready = self._classify_categories(seeds, existing_by_name)

        needs_embed: list[tuple[int, CategoryConfig]] = []
        needs_embed.extend(to_create)
        needs_embed.extend((i, cfg) for i, cfg, _ in to_update)

        embed_map: dict[int, list[float]] = {}
        if needs_embed:
            texts = [self._category_embedding_text(cfg) for _, cfg in needs_embed]
            vecs = await self._get_embedding_client("embedding").embed(texts)
            for (i, _), vec in zip(needs_embed, vecs, strict=True):
                embed_map[i] = vec

        cats: dict[int, Resource] = dict(ready)

        for i, cfg in to_create:
            name = cfg.name.strip() or "Untitled"
            description = cfg.description.strip()
            cat = store.resource_repo.get_or_create_doc(
                lane=lane,
                title=name,
                description=description,
                embedding=embed_map[i],
                user_data=user_data,
                slug=slugify(name),
            )
            cats[i] = cat

        for i, cfg, ex in to_update:
            description = cfg.description.strip()
            cat = store.resource_repo.update_resource(
                resource_id=ex.id, description=description, embedding=embed_map[i]
            )
            cats[i] = cat

        lane_state.doc_ids = []
        lane_state.name_to_id = {}
        for i in range(len(seeds)):
            cat = cats[i]
            lane_state.doc_ids.append(cat.id)
            name = seeds[i].name.strip() or "Untitled"
            lane_state.name_to_id[name.lower()] = cat.id
        lane_state.ready = True

    @staticmethod
    def _category_embedding_text(cat: CategoryConfig) -> str:
        name = cat.name.strip() or "Untitled"
        desc = cat.description.strip()
        return f"{name}: {desc}" if desc else name

    def _map_group_names_to_ids(self, lane: str, names: list[str], ctx: Context) -> list[str]:
        if not names:
            return []
        name_to_id = ctx.lane(lane).name_to_id
        mapped: list[str] = []
        seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            cid = name_to_id.get(key)
            if cid and cid not in seen:
                mapped.append(cid)
                seen.add(cid)
        return mapped

    @staticmethod
    def _partition_group_names(lane: str, names: list[str], ctx: Context) -> tuple[list[str], list[str]]:
        """Split proposed names into (known group ids, unknown names) with dedup."""
        name_to_id = ctx.lane(lane).name_to_id
        known_ids: list[str] = []
        known_seen: set[str] = set()
        unknown: list[str] = []
        unknown_seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            if not key:
                continue
            cid = name_to_id.get(key)
            if cid is not None:
                if cid not in known_seen:
                    known_ids.append(cid)
                    known_seen.add(cid)
            elif key not in unknown_seen:
                unknown.append(name.strip())
                unknown_seen.add(key)
        return known_ids, unknown

    async def _resolve_group_ids(
        self,
        lane: str,
        names: list[str],
        ctx: Context,
        store: Database,
        *,
        user: Mapping[str, Any] | None = None,
    ) -> list[str]:
        """Resolve extractor-proposed group names to lane-doc ids, creating unknown ones.

        Implements the open/adaptive taxonomy per lane: any group name the extractor
        proposes is created on first sight as a ``lane`` doc and cached in the lane's
        context state. Here we only do exact-name dedup.
        """
        if not names:
            return []
        user_data = dict(user or {})
        lane_state = ctx.lane(lane)
        resolved, unknown = self._partition_group_names(lane, names, ctx)
        seen: set[str] = set(resolved)

        if unknown:
            vecs = await self._get_embedding_client("embedding").embed(unknown)
            for name, vec in zip(unknown, vecs, strict=True):
                cat = store.resource_repo.get_or_create_doc(
                    lane=lane,
                    title=name,
                    description="",
                    embedding=vec,
                    user_data=user_data,
                    slug=slugify(name),
                )
                lane_state.name_to_id[name.lower()] = cat.id
                if cat.id not in lane_state.doc_ids:
                    lane_state.doc_ids.append(cat.id)
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

    def _build_entry_type_prompt(
        self, *, entry_type: EntryType, lane_cfg: LaneConfig, resource_text: str, categories_str: str
    ) -> str:
        configured_prompt = lane_cfg.entry_type_prompts.get(entry_type)
        if configured_prompt is None:
            template = ENTRY_TYPE_PROMPTS.get(entry_type)
        elif isinstance(configured_prompt, str):
            template = configured_prompt
        else:
            template = self._resolve_custom_prompt(
                configured_prompt, ENTRY_TYPE_CUSTOM_PROMPTS.get(entry_type, CUSTOM_TYPE_CUSTOM_PROMPTS)
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
                store.entry_repo.update_entry(
                    entry_id=matched_item_id,
                    extra={"ref_id": short_id},
                )

    def _build_group_summary_prompt(
        self,
        *,
        lane: str,
        lane_cfg: LaneConfig,
        category: Resource,
        new_memories: list[str] | list[tuple[str, str]],
    ) -> str:
        """
        Build the prompt for updating an adaptive lane's group-doc summary.

        Args:
            lane: The lane the group doc belongs to.
            lane_cfg: That lane's configuration (summary prompt/length/refs).
            category: The group doc to update.
            new_memories: Either summary strings (legacy) or (item_id, summary) tuples (with refs).
        """
        enable_refs = lane_cfg.enable_item_references

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
        # Per-seed overrides for this lane, falling back to the lane's defaults.
        seed_config = self.lane_category_config_maps.get(lane, {}).get(category.title or "")
        configured_prompt = (seed_config and seed_config.summary_prompt) or lane_cfg.summary_prompt
        if configured_prompt is None:
            prompt = category_summary_prompt
        elif isinstance(configured_prompt, str):
            prompt = configured_prompt
        else:
            prompt = self._resolve_custom_prompt(configured_prompt, category_summary_custom_prompt)
        target_length = (seed_config and seed_config.target_length) or lane_cfg.summary_target_length
        return prompt.format(
            category=self._escape_prompt_value(category.title or ""),
            original_content=self._escape_prompt_value(original or ""),
            new_memory_items_text=self._escape_prompt_value(new_items_text or "No new memory items."),
            target_length=target_length,
        )

    async def _update_group_summaries(
        self,
        lane: str,
        lane_cfg: LaneConfig,
        updates: dict[str, list[tuple[str, str]]] | dict[str, list[str]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
    ) -> dict[str, str]:
        """
        Synthesize an adaptive lane's group-doc summaries from new entries.

        Returns:
            dict mapping group-doc id -> updated summary text
        """
        updated_summaries: dict[str, str] = {}
        if not updates:
            return updated_summaries
        tasks = []
        target_ids: list[str] = []
        client = llm_client or self._get_llm_client()
        for cid, memories in updates.items():
            cat = store.resource_repo.get_resource(cid)
            if not cat or not memories:
                continue
            prompt = self._build_group_summary_prompt(
                lane=lane, lane_cfg=lane_cfg, category=cat, new_memories=memories
            )
            tasks.append(client.chat(prompt))
            target_ids.append(cid)
        if not tasks:
            return updated_summaries
        summaries = await asyncio.gather(*tasks)
        for cid, summary in zip(target_ids, summaries, strict=True):
            cat = store.resource_repo.get_resource(cid)
            if not cat:
                continue
            cleaned_summary = summary.replace("```markdown", "").replace("```", "").strip()
            store.resource_repo.update_resource(
                resource_id=cid,
                summary=cleaned_summary,
            )
            updated_summaries[cid] = cleaned_summary
        return updated_summaries

    def _find_xml_boundaries(self, raw: str) -> tuple[int, int, str] | None:
        """Find the start index, end index, and closing tag for XML root element."""
        root_tags = ["item", "profile", "events", "knowledge"]
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
        else:
            # per_resource lanes (e.g. index) emit a description with no categories.
            memory_dict["categories"] = []

        if memory_dict.get("content"):
            return memory_dict
        return None

    def _parse_entry_type_response_xml(self, raw: str) -> list[dict[str, Any]]:
        """
        Parse XML memory extraction output into a list of memory items.

        Expected XML format (root tag varies by memory type):
        <profile|events|knowledge>
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
