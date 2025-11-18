import asyncio
import json
import logging
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from memu.app.settings import BlobConfig, DatabaseConfig, LLMConfig, MemorizeConfig
from memu.llm.http_client import HTTPLLMClient
from memu.memory.repo import InMemoryStore
from memu.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource
from memu.prompts.category_summary import CATEGORY_SUMMARY_PROMPT
from memu.prompts.memory_type import DEFAULT_MEMORY_TYPES
from memu.prompts.memory_type import PROMPTS as MEMORY_TYPE_PROMPTS
from memu.prompts.preprocess import PROMPTS as PREPROCESS_PROMPTS
from memu.prompts.retrieve.judger import PROMPT as RETRIEVE_JUDGER_PROMPT
from memu.prompts.retrieve.query_rewriter import PROMPT as QUERY_REWRITER_PROMPT
from memu.storage.local_fs import LocalFS
from memu.utils.video import VideoFrameExtractor
from memu.vector.index import cosine_topk

logger = logging.getLogger(__name__)


TConfigModel = TypeVar("TConfigModel", bound=BaseModel)


class MemoryUser:
    def __init__(
        self,
        *,
        llm_config: dict[str, Any] | LLMConfig | None = None,
        blob_config: dict[str, Any] | BlobConfig | None = None,
        database_config: dict[str, Any] | DatabaseConfig | None = None,
        memorize_config: dict[str, Any] | MemorizeConfig | None = None,
    ):
        self.llm_config = self._validate_config(llm_config, LLMConfig)
        self.blob_config = self._validate_config(blob_config, BlobConfig)
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.memorize_config = self._validate_config(memorize_config, MemorizeConfig)
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
        query: str,
        *,
        conversation_history: list[dict[str, str]] | None = None,
        method: str = "rag",
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Retrieve relevant memories based on the query.

        Args:
            query: The search query
            conversation_history: Optional conversation history for query rewriting
            method: Retrieval method - "rag" (vector similarity) or "llm" (LLM-based ranking)
            top_k: Number of top results to return

        Returns:
            Dictionary containing original_query, rewritten_query, method, and retrieved results
        """
        # Rewrite query if conversation history is provided
        original_query = query
        rewritten_query = query

        if conversation_history:
            rewritten_query = await self._rewrite_query_with_history(query, conversation_history)
            logger.debug(f"Original query: {original_query}")
            logger.debug(f"Rewritten query: {rewritten_query}")

        response: dict[str, Any] = {
            "original_query": original_query,
            "rewritten_query": rewritten_query,
            "method": method,
            "resources": [],
            "items": [],
            "categories": [],
        }

        if method == "rag":
            return await self._retrieve_rag(rewritten_query, response, top_k)
        elif method == "llm":
            return await self._retrieve_llm(rewritten_query, response, top_k)
        else:
            msg = f"Unknown retrieval method '{method}'. Use 'rag' or 'llm'."
            raise ValueError(msg)

    async def _retrieve_rag(self, query: str, response: dict[str, Any], top_k: int) -> dict[str, Any]:
        """RAG-based retrieval using vector similarity search"""
        # Use query for embedding
        qvec = (await self.openai.embed([query]))[0]
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

    async def _retrieve_llm(self, query: str, response: dict[str, Any], top_k: int) -> dict[str, Any]:
        """LLM-based retrieval using language model to rank and select memories"""
        # Get all available memories
        all_categories = list(self.store.categories.values())
        all_items = list(self.store.items.values())
        all_resources = list(self.store.resources.values())

        # Use LLM to select and rank relevant memories
        if all_categories:
            selected_categories = await self._llm_rank_memories(query, all_categories, "categories", top_k)
            response["categories"] = selected_categories

        if all_items:
            selected_items = await self._llm_rank_memories(query, all_items, "items", top_k)
            response["items"] = selected_items

        if all_resources:
            selected_resources = await self._llm_rank_memories(query, all_resources, "resources", top_k)
            response["resources"] = selected_resources

        return response

    async def _llm_rank_memories(
        self, query: str, memories: list[Any], memory_type: str, top_k: int
    ) -> list[dict[str, Any]]:
        """Use LLM to rank and select relevant memories"""
        if not memories:
            return []

        # Limit to top 20 to avoid token limits
        sample_size = min(len(memories), 20)
        memories_to_rank = memories[:sample_size]

        # Format memories for LLM
        formatted_memories = []
        for idx, mem in enumerate(memories_to_rank):
            if memory_type == "categories":
                content = f"Category: {mem.name}\nSummary: {mem.summary or 'N/A'}"
            elif memory_type == "items":
                content = f"Item: {mem.summary}"
            else:  # resources
                content = f"Resource: {mem.caption or mem.url}"
            formatted_memories.append(f"[{idx}] {content}")

        memories_text = "\n\n".join(formatted_memories)

        # Create prompt for LLM ranking
        prompt = f"""Given the query and a list of memories, select the top {top_k} most relevant memories.
Return only the indices (numbers) of the selected memories, separated by commas.

Query: {query}

Memories:
{memories_text}

Output format: 0,3,7,... (indices only, comma-separated)
Selected indices:"""

        response_text = await self.openai.summarize(prompt, system_prompt=None)

        # Parse selected indices
        selected_indices = self._parse_llm_indices(response_text, len(memories_to_rank))

        # Return selected memories
        result = []
        for idx in selected_indices[:top_k]:
            mem = memories_to_rank[idx]
            mem_dict = {
                "id": mem.id,
                "score": 1.0 - (selected_indices.index(idx) * 0.1),  # Decreasing score
            }
            if memory_type == "categories":
                mem_dict.update({"name": mem.name, "summary": mem.summary})
            elif memory_type == "items":
                mem_dict.update({"summary": mem.summary, "memory_type": mem.memory_type})
            else:
                mem_dict.update({"url": mem.url, "caption": mem.caption})
            result.append(mem_dict)

        return result

    def _parse_llm_indices(self, response: str, max_idx: int) -> list[int]:
        """Parse indices from LLM response"""
        # Extract numbers from response
        numbers = re.findall(r"\d+", response)
        indices = []
        for num_str in numbers:
            idx = int(num_str)
            if 0 <= idx < max_idx and idx not in indices:
                indices.append(idx)
        return indices

    async def _rewrite_query_with_history(self, query: str, conversation_history: list[dict[str, str]]) -> str:
        """Rewrite query using conversation history to resolve references"""
        # Format conversation history
        history_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in conversation_history
        ])

        # Create prompt for query rewriting
        prompt = QUERY_REWRITER_PROMPT.format(
            conversation_history=self._escape_prompt_value(history_text), query=self._escape_prompt_value(query)
        )

        # Get rewritten query from LLM
        response = await self.openai.summarize(prompt, system_prompt=None)

        # Parse the rewritten query from the response
        rewritten_query = self._parse_rewritten_query(response)
        return rewritten_query or query  # Fall back to original if parsing fails

    def _parse_rewritten_query(self, response: str) -> str | None:
        """Parse rewritten query from LLM response"""
        # Try to extract content between <rewritten_query> tags
        match = re.search(r"<rewritten_query>\s*(.*?)\s*</rewritten_query>", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        # If no tags found, return the response as is (fallback)
        return response.strip()

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
