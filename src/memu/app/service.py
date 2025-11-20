import asyncio
import json
import logging
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from memu.app.settings import BlobConfig, DatabaseConfig, LLMConfig, MemorizeConfig, RetrieveConfig
from memu.llm.http_client import HTTPLLMClient
from memu.memory.repo import InMemoryStore
from memu.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource
from memu.prompts.category_summary import CATEGORY_SUMMARY_PROMPT
from memu.prompts.memory_type import DEFAULT_MEMORY_TYPES
from memu.prompts.memory_type import PROMPTS as MEMORY_TYPE_PROMPTS
from memu.prompts.preprocess import PROMPTS as PREPROCESS_PROMPTS
from memu.prompts.retrieve.llm_category_ranker import PROMPT as LLM_CATEGORY_RANKER_PROMPT
from memu.prompts.retrieve.llm_item_ranker import PROMPT as LLM_ITEM_RANKER_PROMPT
from memu.prompts.retrieve.llm_resource_ranker import PROMPT as LLM_RESOURCE_RANKER_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import SYSTEM_PROMPT as PRE_RETRIEVAL_SYSTEM_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import USER_PROMPT as PRE_RETRIEVAL_USER_PROMPT
from memu.storage.local_fs import LocalFS
from memu.utils.video import VideoFrameExtractor
from memu.vector.index import cosine_topk

logger = logging.getLogger(__name__)


TConfigModel = TypeVar("TConfigModel", bound=BaseModel)


class MemoryService:
    def __init__(
        self,
        *,
        llm_config: LLMConfig | dict[str, Any] | None = None,
        blob_config: BlobConfig | dict[str, Any] | None = None,
        database_config: DatabaseConfig | dict[str, Any] | None = None,
        memorize_config: MemorizeConfig | dict[str, Any] | None = None,
        retrieve_config: RetrieveConfig | dict[str, Any] | None = None,
    ):
        self.llm_config = self._validate_config(llm_config, LLMConfig)
        self.blob_config = self._validate_config(blob_config, BlobConfig)
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.memorize_config = self._validate_config(memorize_config, MemorizeConfig)
        self.retrieve_config = self._validate_config(retrieve_config, RetrieveConfig)
        self.fs = LocalFS(self.blob_config.resources_dir)
        self.store = InMemoryStore()
        backend = self.llm_config.client_backend
        self.openai: Any
        client_kwargs: dict[str, Any] = {
            "base_url": self.llm_config.base_url,
            "api_key": self.llm_config.api_key,
            "chat_model": self.llm_config.chat_model,
            "embed_model": self.llm_config.embed_model,
        }
        if backend == "sdk":
            from memu.llm.openai_sdk import OpenAISDKClient

            self.openai = OpenAISDKClient(**client_kwargs)
        elif backend == "httpx":
            self.openai = HTTPLLMClient(
                provider=self.llm_config.provider,
                endpoint_overrides=self.llm_config.endpoint_overrides,
                **client_kwargs,
            )
        else:
            msg = f"Unknown llm_client_backend '{self.llm_config.client_backend}'"
            raise ValueError(msg)

        self.category_configs: list[dict[str, str]] = list(self.memorize_config.memory_categories or [])
        self._category_prompt_str = self._format_categories_for_prompt(self.category_configs)
        self._category_ids: list[str] = []
        self._category_name_to_id: dict[str, str] = {}
        self._categories_ready = not bool(self.category_configs)
        self._category_init_task: asyncio.Task | None = None
        self._start_category_initialization()

    async def memorize(self, *, resource_url: str, modality: str, summary_prompt: str | None = None) -> dict[str, Any]:
        local_path, text, caption, segments = await self._fetch_and_preprocess_resource(resource_url, modality)

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
            segments=segments,
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
    ) -> tuple[str, str | None, str | None, list[dict[str, int]] | None]:
        local_path, text = await self.fs.fetch(resource_url, modality)
        processed_text, caption, segments = await self._preprocess_resource_url(
            local_path=local_path, text=text, modality=modality
        )
        return local_path, processed_text, caption, segments

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
        configured_types = self.memorize_config.memory_types or DEFAULT_MEMORY_TYPES
        return [cast(MemoryType, mtype) for mtype in configured_types]

    def _resolve_summary_prompt(self, modality: str, override: str | None) -> str:
        memo_settings = self.memorize_config
        return override or memo_settings.summary_prompts.get(modality) or memo_settings.default_summary_prompt

    async def _generate_structured_entries(
        self,
        *,
        resource_url: str,
        modality: str,
        memory_types: list[MemoryType],
        text: str | None,
        base_prompt: str,
        categories_prompt_str: str,
        segments: list[dict[str, int]] | None = None,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        if not memory_types:
            return []

        if text:
            entries = await self._generate_text_entries(
                resource_text=text,
                modality=modality,
                memory_types=memory_types,
                base_prompt=base_prompt,
                categories_prompt_str=categories_prompt_str,
                segments=segments,
            )
            if entries:
                return entries
            no_result_entry = self._build_no_result_fallback(memory_types[0], resource_url, modality)
            return [no_result_entry]

        return self._build_no_text_fallback(memory_types, resource_url, modality)

    async def _generate_text_entries(
        self,
        *,
        resource_text: str,
        modality: str,
        memory_types: list[MemoryType],
        base_prompt: str,
        categories_prompt_str: str,
        segments: list[dict[str, int]] | None,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        if modality == "conversation" and segments:
            segment_entries = await self._generate_entries_for_segments(
                resource_text=resource_text,
                segments=segments,
                memory_types=memory_types,
                base_prompt=base_prompt,
                categories_prompt_str=categories_prompt_str,
            )
            if segment_entries:
                return segment_entries
        return await self._generate_entries_from_text(
            resource_text=resource_text,
            memory_types=memory_types,
            base_prompt=base_prompt,
            categories_prompt_str=categories_prompt_str,
        )

    async def _generate_entries_for_segments(
        self,
        *,
        resource_text: str,
        segments: list[dict[str, int]],
        memory_types: list[MemoryType],
        base_prompt: str,
        categories_prompt_str: str,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        entries: list[tuple[MemoryType, str, list[str]]] = []
        lines = resource_text.split("\n")
        max_idx = len(lines) - 1
        for segment in segments:
            start_idx = segment.get("start", 0)
            end_idx = segment.get("end", max_idx)
            segment_text = self._extract_segment_text(lines, start_idx, end_idx)
            if not segment_text:
                continue
            segment_entries = await self._generate_entries_from_text(
                resource_text=segment_text,
                memory_types=memory_types,
                base_prompt=base_prompt,
                categories_prompt_str=categories_prompt_str,
            )
            entries.extend(segment_entries)
        return entries

    async def _generate_entries_from_text(
        self,
        *,
        resource_text: str,
        memory_types: list[MemoryType],
        base_prompt: str,
        categories_prompt_str: str,
    ) -> list[tuple[MemoryType, str, list[str]]]:
        if not memory_types:
            return []
        prompts = [
            self._build_memory_type_prompt(
                memory_type=mtype,
                resource_text=resource_text,
                categories_str=categories_prompt_str,
            )
            for mtype in memory_types
        ]
        tasks = [self.openai.summarize(prompt_text, system_prompt=base_prompt) for prompt_text in prompts]
        responses = await asyncio.gather(*tasks)
        return self._parse_structured_entries(memory_types, responses)

    def _parse_structured_entries(
        self, memory_types: list[MemoryType], responses: Sequence[str]
    ) -> list[tuple[MemoryType, str, list[str]]]:
        entries: list[tuple[MemoryType, str, list[str]]] = []
        for mtype, response in zip(memory_types, responses, strict=True):
            parsed = self._parse_memory_type_response(response)
            if not parsed:
                fallback_entry = response.strip()
                if fallback_entry:
                    entries.append((mtype, fallback_entry, []))
                continue
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

    async def _preprocess_resource_url(
        self, *, local_path: str, text: str | None, modality: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """
        Preprocess resource based on modality.

        General preprocessing dispatcher for all modalities:
        - Text-based modalities (conversation, document): require text content
        - Audio modality: transcribe audio file first, then process as text
        - Media modalities (video, image): process media files directly

        Args:
            local_path: Local file path to the resource
            text: Text content if available (for text-based modalities)
            modality: Resource modality type

        Returns:
            Tuple of (processed_text, caption, segments)
        """
        template = PREPROCESS_PROMPTS.get(modality)
        if not template:
            return text, None, None

        if modality == "audio":
            text = await self._prepare_audio_text(local_path, text)
            if text is None:
                return None, None, None

        if self._modality_requires_text(modality) and not text:
            return text, None, None

        return await self._dispatch_preprocessor(
            modality=modality,
            local_path=local_path,
            text=text,
            template=template,
        )

    async def _prepare_audio_text(self, local_path: str, text: str | None) -> str | None:
        """Ensure audio resources provide text either via transcription or file read."""
        if text:
            return text

        audio_extensions = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
        text_extensions = {".txt", ".text"}
        file_ext = pathlib.Path(local_path).suffix.lower()

        if file_ext in audio_extensions:
            try:
                logger.info(f"Transcribing audio file: {local_path}")
                transcribed = cast(str, await self.openai.transcribe(local_path))
                logger.info(f"Audio transcription completed: {len(transcribed)} characters")
            except Exception:
                logger.exception("Audio transcription failed for %s", local_path)
                return None
            else:
                return transcribed

        if file_ext in text_extensions:
            path_obj = pathlib.Path(local_path)
            try:
                text_content = path_obj.read_text(encoding="utf-8")
                logger.info(f"Read pre-transcribed text file: {len(text_content)} characters")
            except Exception:
                logger.exception("Failed to read text file %s", local_path)
                return None
            else:
                return text_content

        logger.warning(f"Unknown audio file type: {file_ext}, skipping transcription")
        return None

    def _modality_requires_text(self, modality: str) -> bool:
        return modality in ("conversation", "document")

    async def _dispatch_preprocessor(
        self,
        *,
        modality: str,
        local_path: str,
        text: str | None,
        template: str,
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        if modality == "conversation" and text is not None:
            return await self._preprocess_conversation(text, template)
        if modality == "video":
            return await self._preprocess_video(local_path, template)
        if modality == "image":
            return await self._preprocess_image(local_path, template)
        if modality == "document" and text is not None:
            return await self._preprocess_document(text, template)
        if modality == "audio" and text is not None:
            return await self._preprocess_audio(text, template)
        return text, None, None

    async def _preprocess_conversation(
        self, text: str, template: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """Preprocess conversation data with segmentation"""
        preprocessed_text = self._add_conversation_indices(text)
        prompt = template.format(conversation=self._escape_prompt_value(preprocessed_text))
        processed = await self.openai.summarize(prompt, system_prompt=None)
        conv, summary, segments = self._parse_conversation_preprocess_with_segments(processed, preprocessed_text)
        return conv or preprocessed_text, summary, segments

    async def _preprocess_video(
        self, local_path: str, template: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """
        Preprocess video data - extract description and caption using Vision API.

        Extracts the middle frame from the video and analyzes it using Vision API.

        Args:
            local_path: Path to the video file
            template: Prompt template for video analysis

        Returns:
            Tuple of (description, caption, None)
        """
        try:
            # Check if ffmpeg is available
            if not VideoFrameExtractor.is_ffmpeg_available():
                logger.warning("ffmpeg not available, cannot process video. Returning None.")
                return None, None, None

            # Extract middle frame from video
            logger.info(f"Extracting frame from video: {local_path}")
            frame_path = VideoFrameExtractor.extract_middle_frame(local_path)

            try:
                # Call Vision API with extracted frame
                logger.info(f"Analyzing video frame with Vision API: {frame_path}")
                processed = await self.openai.vision(prompt=template, image_path=frame_path, system_prompt=None)
                description, caption = self._parse_multimodal_response(processed, "detailed_description", "caption")
                return description, caption, None
            finally:
                # Clean up temporary frame file
                import pathlib

                try:
                    pathlib.Path(frame_path).unlink(missing_ok=True)
                    logger.debug(f"Cleaned up temporary frame: {frame_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up frame {frame_path}: {e}")

        except Exception as e:
            logger.error(f"Video preprocessing failed: {e}", exc_info=True)
            return None, None, None

    async def _preprocess_image(
        self, local_path: str, template: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """
        Preprocess image data - extract description and caption using Vision API.

        Args:
            local_path: Path to the image file
            template: Prompt template for image analysis

        Returns:
            Tuple of (description, caption, None)
        """
        # Call Vision API with image
        processed = await self.openai.vision(prompt=template, image_path=local_path, system_prompt=None)
        description, caption = self._parse_multimodal_response(processed, "detailed_description", "caption")
        return description, caption, None

    async def _preprocess_document(
        self, text: str, template: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """Preprocess document data - condense and extract caption"""
        prompt = template.format(document_text=self._escape_prompt_value(text))
        processed = await self.openai.summarize(prompt, system_prompt=None)
        processed_content, caption = self._parse_multimodal_response(processed, "processed_content", "caption")
        return processed_content or text, caption, None

    async def _preprocess_audio(
        self, text: str, template: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """Preprocess audio data - format transcription and extract caption"""
        prompt = template.format(transcription=self._escape_prompt_value(text))
        processed = await self.openai.summarize(prompt, system_prompt=None)
        processed_content, caption = self._parse_multimodal_response(processed, "processed_content", "caption")
        return processed_content or text, caption, None

    def _format_categories_for_prompt(self, categories: list[dict[str, str]]) -> str:
        if not categories:
            return "No categories provided."
        lines = []
        for cat in categories:
            name = (cat.get("name") or "").strip() or "Untitled"
            desc = (cat.get("description") or "").strip()
            lines.append(f"- {name}: {desc}" if desc else f"- {name}")
        return "\n".join(lines)

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
        template = (
            self.memorize_config.memory_type_prompts.get(memory_type) or MEMORY_TYPE_PROMPTS.get(memory_type) or ""
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
            target_length=self.memorize_config.category_summary_target_length,
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

    def _parse_multimodal_response(self, raw: str, content_tag: str, caption_tag: str) -> tuple[str | None, str | None]:
        """
        Parse multimodal preprocessing response (video, image, document, audio).
        Extracts content and caption from XML-like tags.

        Args:
            raw: Raw LLM response
            content_tag: Tag name for main content (e.g., "detailed_description", "processed_content")
            caption_tag: Tag name for caption (typically "caption")

        Returns:
            Tuple of (content, caption)
        """
        content = self._extract_tag_content(raw, content_tag)
        caption = self._extract_tag_content(raw, caption_tag)

        # Fallback: if no tags found, try to use raw response as content
        if not content:
            content = raw.strip()

        # Fallback for caption: use first sentence of content if no caption found
        if not caption and content:
            first_sentence = content.split(".")[0]
            caption = first_sentence if len(first_sentence) <= 200 else first_sentence[:200]

        return content, caption

    def _parse_conversation_preprocess_with_segments(
        self, raw: str, original_text: str
    ) -> tuple[str | None, str | None, list[dict[str, int]] | None]:
        """
        Parse conversation preprocess response and extract segments.
        Returns: (conversation_text, summary, segments)
        """
        conversation = self._extract_tag_content(raw, "conversation")
        summary = self._extract_tag_content(raw, "summary")
        segments = self._extract_segments_with_fallback(raw)
        return conversation, summary, segments

    def _extract_segments_with_fallback(self, raw: str) -> list[dict[str, int]] | None:
        segments = self._segments_from_json_payload(raw)
        if segments is not None:
            return segments
        try:
            blob = self._extract_json_blob(raw)
        except Exception:
            logging.exception("Failed to extract segments from conversation preprocess response")
            return None
        return self._segments_from_json_payload(blob)

    def _segments_from_json_payload(self, payload: str) -> list[dict[str, int]] | None:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError, TypeError:
            return None
        return self._segments_from_parsed_data(parsed)

    @staticmethod
    def _segments_from_parsed_data(parsed: Any) -> list[dict[str, int]] | None:
        if not isinstance(parsed, dict):
            return None
        segments_data = parsed.get("segments")
        if not isinstance(segments_data, list):
            return None
        segments: list[dict[str, int]] = []
        for seg in segments_data:
            if isinstance(seg, dict) and "start" in seg and "end" in seg:
                try:
                    segments.append({"start": int(seg["start"]), "end": int(seg["end"])})
                except TypeError, ValueError:
                    continue
        return segments or None

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

    @staticmethod
    def _validate_config(
        config: Mapping[str, Any] | BaseModel | None,
        model_type: type[TConfigModel],
    ) -> TConfigModel:
        if isinstance(config, model_type):
            return config
        if config is None:
            return model_type()
        return model_type.model_validate(config)

    async def retrieve(
        self,
        queries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Retrieve relevant memories based on the query using either RAG-based or LLM-based search.

        Args:
            queries: List of query messages in format [{"role": "user", "content": {"text": "..."}}].
                     The last one is the current query, others are context.
                     If list has only 1 element, no query rewriting is performed.

        Returns:
            Dictionary containing:
            - "needs_retrieval": bool - Whether retrieval was performed
            - "rewritten_query": str - Query after rewriting with context (if retrieval performed)
            - "next_step_query": str | None - Suggested query for the next retrieval step (if applicable)
            - "categories": list - Retrieved categories
            - "items": list - Retrieved items
            - "resources": list - Retrieved resources

        Notes:
            - RAG (rag) method is faster and more efficient for large datasets
            - LLM (llm) method may provide better semantic understanding but is slower and more expensive
            - LLM method includes reasoning for each ranked result
            - Pre-retrieval decision checks if retrieval is needed based on query type
            - Query rewriting incorporates query context for better results (if queries > 1)
        """
        if not queries:
            raise ValueError("empty_queries")

        # Extract text from the query structure
        current_query = self._extract_query_text(queries[-1])
        context_queries_objs = queries[:-1] if len(queries) > 1 else []

        # Step 1: Decide if retrieval is needed
        needs_retrieval, rewritten_query = await self._decide_if_retrieval_needed(
            current_query, context_queries_objs, retrieved_content=None
        )

        # If only one query, do not use the rewritten version (use original)
        if len(queries) == 1:
            rewritten_query = current_query

        if not needs_retrieval:
            logger.info(f"Query does not require retrieval: {current_query}")
            return {
                "needs_retrieval": False,
                "original_query": current_query,
                "rewritten_query": rewritten_query,
                "next_step_query": None,
                "categories": [],
                "items": [],
                "resources": [],
            }

        logger.info(f"Query rewritten: '{current_query}' -> '{rewritten_query}'")

        # Step 2: Perform retrieval with rewritten query using configured method
        if self.retrieve_config.method == "llm":
            results = await self._llm_based_retrieve(
                rewritten_query, top_k=self.retrieve_config.top_k, context_queries=context_queries_objs
            )
        else:  # rag
            results = await self._embedding_based_retrieve(
                rewritten_query, top_k=self.retrieve_config.top_k, context_queries=context_queries_objs
            )

        # Add metadata
        results["needs_retrieval"] = True
        results["original_query"] = current_query
        results["rewritten_query"] = rewritten_query
        if "next_step_query" not in results:
            results["next_step_query"] = None

        return results

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

    async def _decide_if_retrieval_needed(
        self,
        query: str,
        context_queries: list[dict[str, Any]] | None,
        retrieved_content: str | None = None,
        system_prompt: str | None = None,
    ) -> tuple[bool, str]:
        """
        Decide if the query requires memory retrieval (or MORE retrieval) and rewrite it with context.

        Args:
            query: The current query string
            context_queries: List of previous query objects with role and content
            retrieved_content: Content retrieved so far (if checking for sufficiency)
            system_prompt: Optional system prompt override

        Returns:
            Tuple of (needs_retrieval: bool, rewritten_query: str)
            - needs_retrieval: True if retrieval/more retrieval is needed
            - rewritten_query: The rewritten query for the next step
        """
        history_text = self._format_query_context(context_queries)
        content_text = retrieved_content or "No content retrieved yet."

        prompt = PRE_RETRIEVAL_USER_PROMPT.format(
            query=self._escape_prompt_value(query),
            conversation_history=self._escape_prompt_value(history_text),
            retrieved_content=self._escape_prompt_value(content_text),
        )

        sys_prompt = system_prompt or PRE_RETRIEVAL_SYSTEM_PROMPT
        response = await self.openai.summarize(prompt, system_prompt=sys_prompt)
        decision = self._extract_decision(response)
        rewritten = self._extract_rewritten_query(response) or query

        return decision == "RETRIEVE", rewritten

    def _format_query_context(self, queries: list[dict[str, Any]] | None) -> str:
        """Format query context for prompts, including role information"""
        if not queries:
            return "No query context."

        lines = []
        for q in queries:
            if isinstance(q, str):
                # Backward compatibility
                lines.append(f"- {q}")
            elif isinstance(q, dict):
                role = q.get("role", "user")
                content = q.get("content")
                if isinstance(content, dict):
                    text = content.get("text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                lines.append(f"- [{role}]: {text}")
            else:
                lines.append(f"- {q!s}")

        return "\n".join(lines)

    @staticmethod
    def _extract_query_text(query: dict[str, Any]) -> str:
        """
        Extract text content from query message structure.

        Args:
            query: Query in format {"role": "user", "content": {"text": "..."}}

        Returns:
            The extracted text string
        """
        if isinstance(query, str):
            # Backward compatibility: if it's already a string, return it
            return query

        if not isinstance(query, dict):
            raise TypeError("INVALID")

        content = query.get("content")
        if isinstance(content, dict):
            text = content.get("text", "")
            if not text:
                raise ValueError("EMPTY")
            return str(text)
        elif isinstance(content, str):
            # Also support {"role": "user", "content": "text"} format
            return content
        else:
            raise TypeError("INVALID")

    def _extract_decision(self, raw: str) -> str:
        """Extract RETRIEVE or NO_RETRIEVE decision from LLM response"""
        if not raw:
            return "RETRIEVE"  # Default to retrieve if uncertain

        match = re.search(r"<decision>(.*?)</decision>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            decision = match.group(1).strip().upper()
            if "NO_RETRIEVE" in decision or "NO RETRIEVE" in decision:
                return "NO_RETRIEVE"
            if "RETRIEVE" in decision:
                return "RETRIEVE"

        upper = raw.strip().upper()
        if "NO_RETRIEVE" in upper or "NO RETRIEVE" in upper:
            return "NO_RETRIEVE"

        return "RETRIEVE"  # Default to retrieve

    def _extract_rewritten_query(self, raw: str) -> str | None:
        """Extract rewritten query from LLM response"""
        match = re.search(r"<rewritten_query>(.*?)</rewritten_query>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    async def _embedding_based_retrieve(
        self, query: str, top_k: int, context_queries: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """Embedding-based retrieval with query rewriting and judging at each tier"""
        current_query = query
        qvec = (await self.openai.embed([current_query]))[0]
        response: dict[str, Any] = {"resources": [], "items": [], "categories": [], "next_step_query": None}
        content_sections: list[str] = []

        # Tier 1: Categories
        cat_hits, summary_lookup = await self._rank_categories_by_summary(qvec, top_k)
        if cat_hits:
            response["categories"] = self._materialize_hits(cat_hits, self.store.categories)
            content_sections.append(self._format_category_content(cat_hits, summary_lookup))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query, context_queries, retrieved_content="\n\n".join(content_sections)
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response
            # Re-embed with rewritten query
            qvec = (await self.openai.embed([current_query]))[0]

        # Tier 2: Items
        item_hits = cosine_topk(qvec, [(i.id, i.embedding) for i in self.store.items.values()], k=top_k)
        if item_hits:
            response["items"] = self._materialize_hits(item_hits, self.store.items)
            content_sections.append(self._format_item_content(item_hits))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query, context_queries, retrieved_content="\n\n".join(content_sections)
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response
            # Re-embed with rewritten query
            qvec = (await self.openai.embed([current_query]))[0]

        # Tier 3: Resources
        resource_corpus = self._resource_caption_corpus()
        if resource_corpus:
            res_hits = cosine_topk(qvec, resource_corpus, k=top_k)
            if res_hits:
                response["resources"] = self._materialize_hits(res_hits, self.store.resources)
                content_sections.append(self._format_resource_content(res_hits))

        return response

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

    async def _llm_based_retrieve(
        self, query: str, top_k: int, context_queries: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """
        LLM-based retrieval that uses language model to search and rank results
        in a hierarchical manner, with query rewriting and judging at each tier.

        Flow:
        1. Search categories with LLM, judge + rewrite query
        2. If needs more, search items from relevant categories, judge + rewrite
        3. If needs more, search resources related to context
        """
        current_query = query
        response: dict[str, Any] = {"resources": [], "items": [], "categories": [], "next_step_query": None}
        content_sections: list[str] = []

        # Tier 1: Search and rank categories
        category_hits = await self._llm_rank_categories(current_query, top_k)
        if category_hits:
            response["categories"] = category_hits
            content_sections.append(self._format_llm_category_content(category_hits))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query, context_queries, retrieved_content="\n\n".join(content_sections)
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response

        # Tier 2: Search memory items from relevant categories
        relevant_category_ids = [cat["id"] for cat in category_hits]
        item_hits = await self._llm_rank_items(current_query, top_k, relevant_category_ids, category_hits)
        if item_hits:
            response["items"] = item_hits
            content_sections.append(self._format_llm_item_content(item_hits))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query, context_queries, retrieved_content="\n\n".join(content_sections)
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response

        # Tier 3: Search resources related to the context
        resource_hits = await self._llm_rank_resources(current_query, top_k, category_hits, item_hits)
        if resource_hits:
            response["resources"] = resource_hits
            content_sections.append(self._format_llm_resource_content(resource_hits))

        return response

    def _format_categories_for_llm(self, category_ids: list[str] | None = None) -> str:
        """Format categories for LLM consumption"""
        categories_to_format = self.store.categories
        if category_ids:
            categories_to_format = {cid: cat for cid, cat in self.store.categories.items() if cid in category_ids}

        if not categories_to_format:
            return "No categories available."

        lines = []
        for cid, cat in categories_to_format.items():
            lines.append(f"ID: {cid}")
            lines.append(f"Name: {cat.name}")
            if cat.description:
                lines.append(f"Description: {cat.description}")
            if cat.summary:
                lines.append(f"Summary: {cat.summary}")
            lines.append("---")

        return "\n".join(lines)

    def _format_items_for_llm(self, category_ids: list[str] | None = None) -> str:
        """Format memory items for LLM consumption, optionally filtered by category"""
        items_to_format = []
        seen_item_ids = set()

        if category_ids:
            # Get items that belong to the specified categories
            for rel in self.store.relations:
                if rel.category_id in category_ids:
                    item = self.store.items.get(rel.item_id)
                    if item and item.id not in seen_item_ids:
                        items_to_format.append(item)
                        seen_item_ids.add(item.id)
        else:
            items_to_format = list(self.store.items.values())

        if not items_to_format:
            return "No memory items available."

        lines = []
        for item in items_to_format:
            lines.append(f"ID: {item.id}")
            lines.append(f"Type: {item.memory_type}")
            lines.append(f"Summary: {item.summary}")
            lines.append("---")

        return "\n".join(lines)

    def _format_resources_for_llm(self, item_ids: list[str] | None = None) -> str:
        """Format resources for LLM consumption, optionally filtered by related items"""
        resources_to_format = []

        if item_ids:
            # Get resources that are related to the specified items
            resource_ids = {self.store.items[iid].resource_id for iid in item_ids if iid in self.store.items}
            resources_to_format = [self.store.resources[rid] for rid in resource_ids if rid in self.store.resources]
        else:
            resources_to_format = list(self.store.resources.values())

        if not resources_to_format:
            return "No resources available."

        lines = []
        for res in resources_to_format:
            lines.append(f"ID: {res.id}")
            lines.append(f"URL: {res.url}")
            lines.append(f"Modality: {res.modality}")
            if res.caption:
                lines.append(f"Caption: {res.caption}")
            lines.append("---")

        return "\n".join(lines)

    async def _llm_rank_categories(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Use LLM to rank categories based on query relevance"""
        if not self.store.categories:
            return []

        categories_data = self._format_categories_for_llm()
        prompt = LLM_CATEGORY_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            categories_data=self._escape_prompt_value(categories_data),
        )

        llm_response = await self.openai.summarize(prompt, system_prompt=None)
        return self._parse_llm_category_response(llm_response)

    async def _llm_rank_items(
        self, query: str, top_k: int, category_ids: list[str], category_hits: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Use LLM to rank memory items from relevant categories"""
        if not category_ids:
            return []

        items_data = self._format_items_for_llm(category_ids)
        if items_data == "No memory items available.":
            return []

        # Format relevant categories for context
        relevant_categories_info = "\n".join([
            f"- {cat['name']}: {cat.get('summary', cat.get('description', ''))}" for cat in category_hits
        ])

        prompt = LLM_ITEM_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            relevant_categories=self._escape_prompt_value(relevant_categories_info),
            items_data=self._escape_prompt_value(items_data),
        )

        llm_response = await self.openai.summarize(prompt, system_prompt=None)
        return self._parse_llm_item_response(llm_response)

    async def _llm_rank_resources(
        self, query: str, top_k: int, category_hits: list[dict[str, Any]], item_hits: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Use LLM to rank resources related to the context"""
        # Get item IDs to filter resources
        item_ids = [item["id"] for item in item_hits]
        if not item_ids:
            return []

        resources_data = self._format_resources_for_llm(item_ids)
        if resources_data == "No resources available.":
            return []

        # Build context info
        context_parts = []
        if category_hits:
            context_parts.append("Relevant Categories:")
            context_parts.extend([f"- {cat['name']}" for cat in category_hits])
        if item_hits:
            context_parts.append("\nRelevant Memory Items:")
            context_parts.extend([f"- {item.get('summary', '')[:100]}..." for item in item_hits[:3]])

        context_info = "\n".join(context_parts)

        prompt = LLM_RESOURCE_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            context_info=self._escape_prompt_value(context_info),
            resources_data=self._escape_prompt_value(resources_data),
        )

        llm_response = await self.openai.summarize(prompt, system_prompt=None)
        return self._parse_llm_resource_response(llm_response)

    def _parse_llm_category_response(self, raw_response: str) -> list[dict[str, Any]]:
        """Parse LLM category ranking response"""
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "categories" in parsed and isinstance(parsed["categories"], list):
                category_ids = parsed["categories"]
                # Return categories in the order provided by LLM (already sorted by relevance)
                for cat_id in category_ids:
                    if isinstance(cat_id, str):
                        cat = self.store.categories.get(cat_id)
                        if cat:
                            cat_data = self._model_dump_without_embeddings(cat)
                            results.append(cat_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM category ranking response: {e}")

        return results

    def _parse_llm_item_response(self, raw_response: str) -> list[dict[str, Any]]:
        """Parse LLM item ranking response"""
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "items" in parsed and isinstance(parsed["items"], list):
                item_ids = parsed["items"]
                # Return items in the order provided by LLM (already sorted by relevance)
                for item_id in item_ids:
                    if isinstance(item_id, str):
                        mem_item = self.store.items.get(item_id)
                        if mem_item:
                            item_data = self._model_dump_without_embeddings(mem_item)
                            results.append(item_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM item ranking response: {e}")

        return results

    def _parse_llm_resource_response(self, raw_response: str) -> list[dict[str, Any]]:
        """Parse LLM resource ranking response"""
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "resources" in parsed and isinstance(parsed["resources"], list):
                resource_ids = parsed["resources"]
                # Return resources in the order provided by LLM (already sorted by relevance)
                for res_id in resource_ids:
                    if isinstance(res_id, str):
                        res = self.store.resources.get(res_id)
                        if res:
                            res_data = self._model_dump_without_embeddings(res)
                            results.append(res_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM resource ranking response: {e}")

        return results

    def _format_llm_category_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked category content for judger"""
        lines = []
        for cat in hits:
            summary = cat.get("summary", "") or cat.get("description", "")
            lines.append(f"Category: {cat['name']}\nSummary: {summary}")
        return "\n\n".join(lines).strip()

    def _format_llm_item_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked item content for judger"""
        lines = []
        for item in hits:
            lines.append(f"Memory Item ({item['memory_type']}): {item['summary']}")
        return "\n\n".join(lines).strip()

    def _format_llm_resource_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked resource content for judger"""
        lines = []
        for res in hits:
            caption = res.get("caption", "") or f"Resource {res['url']}"
            lines.append(f"Resource: {caption}")
        return "\n\n".join(lines).strip()
