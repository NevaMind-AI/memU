from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from typing import Any, cast

from pydantic import BaseModel

from memu.app.settings import AppSettings
from memu.llm.http_client import HTTPLLMClient
from memu.memory.repo import InMemoryStore
from memu.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource
from memu.prompts.category_summary import CATEGORY_SUMMARY_PROMPT
from memu.prompts.memory_type import DEFAULT_MEMORY_TYPES
from memu.prompts.memory_type import PROMPTS as MEMORY_TYPE_PROMPTS
from memu.prompts.preprocess import PROMPTS as PREPROCESS_PROMPTS
from memu.prompts.retrieve.judger import PROMPT as RETRIEVE_JUDGER_PROMPT
from memu.storage.local_fs import LocalFS
from memu.vector.index import cosine_topk


class MemoryService:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.fs = LocalFS(settings.resources_dir)
        self.store = InMemoryStore()
        backend = (settings.llm_client_backend or "httpx").lower()
        self.openai: Any
        client_kwargs: dict[str, Any] = {
            "base_url": settings.openai_base,
            "api_key": settings.openai_api_key,
            "chat_model": settings.chat_model,
            "embed_model": settings.embed_model,
        }
        if backend == "sdk":
            from memu.llm.openai_sdk import OpenAISDKClient

            self.openai = OpenAISDKClient(**client_kwargs)
        elif backend == "httpx":
            self.openai = HTTPLLMClient(
                provider=self.settings.llm_http_provider,
                endpoint_overrides=self.settings.llm_http_endpoints,
                **client_kwargs,
            )
        else:
            msg = f"Unknown llm_client_backend '{settings.llm_client_backend}'"
            raise ValueError(msg)

        self.category_configs: list[dict[str, str]] = list(settings.memory_categories or [])
        self._category_prompt_str = self._format_categories_for_prompt(self.category_configs)
        self._category_ids: list[str] = []
        self._category_name_to_id: dict[str, str] = {}
        self._categories_ready = not bool(self.category_configs)
        self._category_init_task: asyncio.Task | None = None
        self._start_category_initialization()

    async def memorize(self, *, resource_url: str, modality: str, summary_prompt: str | None = None) -> dict[str, Any]:
        local_path, text, caption = await self._fetch_and_preprocess_resource(resource_url, modality)

        await self._ensure_categories_ready()
        cat_ids: list[str] = list(self._category_ids)

        res = await self._create_resource_with_caption(
            resource_url=resource_url,
            modality=modality,
            local_path=local_path,
            caption=caption,
        )

        memory_types = self._resolve_memory_types()
        base_prompt = self._resolve_summary_prompt(modality, summary_prompt)
        categories_prompt_str = self._category_prompt_str

        structured_entries = await self._generate_structured_entries(
            resource_url=resource_url,
            modality=modality,
            memory_types=memory_types,
            text=text,
            base_prompt=base_prompt,
            categories_prompt_str=categories_prompt_str,
        )

        items, rels, category_memory_updates = await self._persist_memory_items(
            resource_id=res.id,
            structured_entries=structured_entries,
        )

        await self._update_category_summaries(category_memory_updates)

        return {
            "resource": self._model_dump_without_embeddings(res),
            "items": [self._model_dump_without_embeddings(item) for item in items],
            "categories": [self._model_dump_without_embeddings(self.store.categories[c]) for c in cat_ids],
            "relations": [r.model_dump() for r in rels],
        }

    async def _fetch_and_preprocess_resource(
        self, resource_url: str, modality: str
    ) -> tuple[str, str | None, str | None]:
        local_path, text = await self.fs.fetch(resource_url, modality)
        processed_text, caption = await self._preprocess_resource_text(text=text, modality=modality)
        return local_path, processed_text, caption

    async def _create_resource_with_caption(
        self, *, resource_url: str, modality: str, local_path: str, caption: str | None
    ) -> Resource:
        res = self.store.create_resource(url=resource_url, modality=modality, local_path=local_path)
        if caption:
            caption_text = caption.strip()
            if caption_text:
                res.caption = caption_text
                res.embedding = (await self.openai.embed([caption_text]))[0]
        return res

    def _resolve_memory_types(self) -> list[MemoryType]:
        configured_types = self.settings.memory_types or DEFAULT_MEMORY_TYPES
        return [cast(MemoryType, mtype) for mtype in configured_types]

    def _resolve_summary_prompt(self, modality: str, override: str | None) -> str:
        return override or self.settings.summary_prompts.get(modality) or self.settings.default_summary_prompt

    async def _generate_structured_entries(
        self,
        *,
        resource_url: str,
        modality: str,
        memory_types: list[MemoryType],
        text: str | None,
        base_prompt: str,
        categories_prompt_str: str,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        structured_entries: list[tuple[MemoryType, str, list[str]]] = []
        if text and memory_types:
            prompts = [
                self._build_memory_type_prompt(
                    memory_type=mtype,
                    resource_text=text,
                    categories_str=categories_prompt_str,
                )
                for mtype in memory_types
            ]
            tasks = [self.openai.summarize(prompt_text, system_prompt=base_prompt) for prompt_text in prompts]
            responses = await asyncio.gather(*tasks)
            for mtype, response in zip(memory_types, responses, strict=True):
                parsed = self._parse_memory_type_response(response)
                if not parsed:
                    fallback_entry = response.strip()
                    if fallback_entry:
                        structured_entries.append((mtype, fallback_entry, []))
                    continue
                for entry in parsed:
                    content = (entry.get("content") or "").strip()
                    if not content:
                        continue
                    cat_names = [c.strip() for c in entry.get("categories", []) if isinstance(c, str) and c.strip()]
                    structured_entries.append((mtype, content, cat_names))
        else:
            fallback = f"Resource {resource_url} ({modality}) stored. No text summary in v0."
            structured_entries = [(mtype, f"{fallback} (memory type: {mtype}).", []) for mtype in memory_types]

        if not structured_entries and memory_types:
            fallback = f"Resource {resource_url} ({modality}) stored. No structured memories generated."
            structured_entries.append((memory_types[0], fallback, []))
        return structured_entries

    async def _persist_memory_items(
        self, *, resource_id: str, structured_entries: list[tuple[MemoryType, str, list[str]]]
    ) -> tuple[list[MemoryItem], list[CategoryItem], dict[str, list[str]]]:
        summary_payloads = [content for _, content, _ in structured_entries]
        item_embeddings = await self.openai.embed(summary_payloads) if summary_payloads else []
        items: list[MemoryItem] = []
        rels: list[CategoryItem] = []
        category_memory_updates: dict[str, list[str]] = {}

        for (memory_type, summary_text, cat_names), emb in zip(structured_entries, item_embeddings, strict=True):
            item = self.store.create_item(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary_text,
                embedding=emb,
            )
            items.append(item)
            mapped_cat_ids = self._map_category_names_to_ids(cat_names)
            for cid in mapped_cat_ids:
                rels.append(self.store.link_item_category(item.id, cid))
                category_memory_updates.setdefault(cid, []).append(summary_text)

        return items, rels, category_memory_updates

    def _start_category_initialization(self) -> None:
        if self._categories_ready:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop:
            self._category_init_task = loop.create_task(self._initialize_categories())
        else:
            asyncio.run(self._initialize_categories())

    async def _ensure_categories_ready(self) -> None:
        if self._categories_ready:
            return
        if self._category_init_task:
            await self._category_init_task
            self._category_init_task = None
            return
        await self._initialize_categories()

    async def _initialize_categories(self) -> None:
        if self._categories_ready:
            return
        if not self.category_configs:
            self._categories_ready = True
            return
        cat_texts = [self._category_embedding_text(cfg) for cfg in self.category_configs]
        cat_vecs = await self.openai.embed(cat_texts)
        self._category_ids = []
        self._category_name_to_id = {}
        for cfg, vec in zip(self.category_configs, cat_vecs, strict=True):
            name = (cfg.get("name") or "").strip() or "Untitled"
            description = (cfg.get("description") or "").strip()
            cat = self.store.get_or_create_category(name=name, description=description, embedding=vec)
            self._category_ids.append(cat.id)
            self._category_name_to_id[name.lower()] = cat.id
        self._categories_ready = True

    @staticmethod
    def _category_embedding_text(cat: dict[str, str]) -> str:
        name = (cat.get("name") or "").strip() or "Untitled"
        desc = (cat.get("description") or "").strip()
        return f"{name}: {desc}" if desc else name

    def _map_category_names_to_ids(self, names: list[str]) -> list[str]:
        if not names:
            return []
        mapped: list[str] = []
        seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            cid = self._category_name_to_id.get(key)
            if cid and cid not in seen:
                mapped.append(cid)
                seen.add(cid)
        return mapped

    async def _preprocess_resource_text(self, *, text: str | None, modality: str) -> tuple[str | None, str | None]:
        if not text:
            return text, None
        template = PREPROCESS_PROMPTS.get(modality)
        if not template:
            return text, None
        prompt = template.format(conversation=self._escape_prompt_value(text))
        processed = await self.openai.summarize(prompt, system_prompt=None)
        if modality == "conversation":
            conv, summary = self._parse_conversation_preprocess(processed)
            return conv or processed, summary
        return processed, None

    def _format_categories_for_prompt(self, categories: list[dict[str, str]]) -> str:
        if not categories:
            return "No categories provided."
        lines = []
        for cat in categories:
            name = (cat.get("name") or "").strip() or "Untitled"
            desc = (cat.get("description") or "").strip()
            lines.append(f"- {name}: {desc}" if desc else f"- {name}")
        return "\n".join(lines)

    def _build_memory_type_prompt(self, *, memory_type: MemoryType, resource_text: str, categories_str: str) -> str:
        template = (
            self.settings.memory_type_prompts.get(memory_type) or MEMORY_TYPE_PROMPTS.get(memory_type) or ""
        ).strip()
        if not template:
            return resource_text
        safe_resource = self._escape_prompt_value(resource_text)
        safe_categories = self._escape_prompt_value(categories_str)
        return template.format(resource=safe_resource, categories_str=safe_categories)

    def _build_category_summary_prompt(self, *, category: MemoryCategory, new_memories: list[str]) -> str:
        new_items_text = "\n".join(f"- {m}" for m in new_memories if m.strip())
        original = category.summary or ""
        prompt = CATEGORY_SUMMARY_PROMPT
        return prompt.format(
            category=self._escape_prompt_value(category.name),
            original_content=self._escape_prompt_value(original or ""),
            new_memory_items_text=self._escape_prompt_value(new_items_text or "No new memory items."),
            target_length=self.settings.category_summary_target_length,
        )

    async def _update_category_summaries(self, updates: dict[str, list[str]]) -> None:
        if not updates:
            return
        tasks = []
        target_ids: list[str] = []
        for cid, memories in updates.items():
            cat = self.store.categories.get(cid)
            if not cat or not memories:
                continue
            prompt = self._build_category_summary_prompt(category=cat, new_memories=memories)
            tasks.append(self.openai.summarize(prompt, system_prompt=None))
            target_ids.append(cid)
        if not tasks:
            return
        summaries = await asyncio.gather(*tasks)
        for cid, summary in zip(target_ids, summaries, strict=True):
            cat = self.store.categories.get(cid)
            if not cat:
                continue
            cat.summary = summary.strip()

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

    @staticmethod
    def _extract_json_blob(raw: str) -> str:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            msg = "No JSON object found"
            raise ValueError(msg)
        return raw[start : end + 1]

    @staticmethod
    def _escape_prompt_value(value: str) -> str:
        return value.replace("{", "{{").replace("}", "}}")

    def _model_dump_without_embeddings(self, obj: BaseModel) -> dict[str, Any]:
        data = obj.model_dump()
        data.pop("embedding", None)
        return data

    async def retrieve(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        qvec = (await self.openai.embed([query]))[0]
        response: dict[str, list[dict[str, Any]]] = {"resources": [], "items": [], "categories": []}
        content_sections: list[str] = []

        cat_hits, summary_lookup = await self._rank_categories_by_summary(qvec, top_k)
        if cat_hits:
            response["categories"] = self._materialize_hits(cat_hits, self.store.categories)
            content_sections.append(self._format_category_content(cat_hits, summary_lookup))
            if await self._judge_retrieval_sufficient(query, "\n\n".join(content_sections)):
                return response

        item_hits = cosine_topk(qvec, [(i.id, i.embedding) for i in self.store.items.values()], k=top_k)
        if item_hits:
            response["items"] = self._materialize_hits(item_hits, self.store.items)
            content_sections.append(self._format_item_content(item_hits))
            if await self._judge_retrieval_sufficient(query, "\n\n".join(content_sections)):
                return response

        resource_corpus = self._resource_caption_corpus()
        if resource_corpus:
            res_hits = cosine_topk(qvec, resource_corpus, k=top_k)
            if res_hits:
                response["resources"] = self._materialize_hits(res_hits, self.store.resources)
                content_sections.append(self._format_resource_content(res_hits))
                await self._judge_retrieval_sufficient(query, "\n\n".join(content_sections))

        return response

    async def _rank_categories_by_summary(
        self, query_vec: list[float], top_k: int
    ) -> tuple[list[tuple[str, float]], dict[str, str]]:
        entries = [(cid, cat.summary) for cid, cat in self.store.categories.items() if cat.summary]
        if not entries:
            return [], {}
        summary_texts = [summary for _, summary in entries]
        summary_embeddings = await self.openai.embed(summary_texts)
        corpus = [(cid, emb) for (cid, _), emb in zip(entries, summary_embeddings, strict=True)]
        hits = cosine_topk(query_vec, corpus, k=top_k)
        summary_lookup = dict(entries)
        return hits, summary_lookup

    def _materialize_hits(self, hits: Sequence[tuple[str, float]], pool: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for _id, score in hits:
            obj = pool.get(_id)
            if not obj:
                continue
            data = self._model_dump_without_embeddings(obj)
            data["score"] = float(score)
            out.append(data)
        return out

    def _format_category_content(self, hits: list[tuple[str, float]], summaries: dict[str, str]) -> str:
        lines = []
        for cid, score in hits:
            cat = self.store.categories.get(cid)
            if not cat:
                continue
            summary = summaries.get(cid) or cat.summary or ""
            lines.append(f"Category: {cat.name}\nSummary: {summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_item_content(self, hits: list[tuple[str, float]]) -> str:
        lines = []
        for iid, score in hits:
            item = self.store.items.get(iid)
            if not item:
                continue
            lines.append(f"Memory Item ({item.memory_type}): {item.summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_resource_content(self, hits: list[tuple[str, float]]) -> str:
        lines = []
        for rid, score in hits:
            res = self.store.resources.get(rid)
            if not res:
                continue
            caption = res.caption or f"Resource {res.url}"
            lines.append(f"Resource: {caption}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _resource_caption_corpus(self) -> list[tuple[str, list[float]]]:
        corpus: list[tuple[str, list[float]]] = []
        for rid, res in self.store.resources.items():
            if res.embedding:
                corpus.append((rid, res.embedding))
        return corpus

    async def _judge_retrieval_sufficient(self, query: str, content: str) -> bool:
        if not content.strip():
            return False
        prompt = RETRIEVE_JUDGER_PROMPT.format(
            query=self._escape_prompt_value(query),
            content=self._escape_prompt_value(content),
        )
        verdict = await self.openai.summarize(prompt, system_prompt=None)
        return self._extract_judgement(verdict) == "ENOUGH"

    def _extract_judgement(self, raw: str) -> str:
        if not raw:
            return "MORE"
        match = re.search(r"<judgement>(.*?)</judgement>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            token = match.group(1).strip().upper()
            if "ENOUGH" in token:
                return "ENOUGH"
            if "MORE" in token:
                return "MORE"
        upper = raw.strip().upper()
        if "ENOUGH" in upper:
            return "ENOUGH"
        return "MORE"
