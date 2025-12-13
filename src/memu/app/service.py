import asyncio
import json
import logging
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from memu.app.settings import (
    BlobConfig,
    DatabaseConfig,
    EmbeddingConfig,
    LLMConfig,
    MemorizeConfig,
    RetrieveConfig,
    UserConfig,
)
from memu.embedding.http_client import HTTPEmbeddingClient
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
from memu.utils.conversation import format_conversation_for_preprocess
from memu.utils.video import VideoFrameExtractor
from memu.vector.index import cosine_topk

logger = logging.getLogger(__name__)


TConfigModel = TypeVar("TConfigModel", bound=BaseModel)


class _UserContext:
    """Per-user in-memory state and category bookkeeping."""

    def __init__(self, *, categories_ready: bool) -> None:
        self.store = InMemoryStore()
        self.category_ids: list[str] = []
        self.category_name_to_id: dict[str, str] = {}
        self.categories_ready = categories_ready
        self.category_init_task: asyncio.Task | None = None


class MemoryService:
    def __init__(
        self,
        *,
        llm_config: LLMConfig | dict[str, Any] | None = None,
        embedding_config: EmbeddingConfig | dict[str, Any] | None = None,
        blob_config: BlobConfig | dict[str, Any] | None = None,
        database_config: DatabaseConfig | dict[str, Any] | None = None,
        memorize_config: MemorizeConfig | dict[str, Any] | None = None,
        retrieve_config: RetrieveConfig | dict[str, Any] | None = None,
        user_config: UserConfig | dict[str, Any] | None = None,
    ):
        self.llm_config = self._validate_config(llm_config, LLMConfig)
        self.embedding_config = self._validate_config(embedding_config, EmbeddingConfig)
        self.blob_config = self._validate_config(blob_config, BlobConfig)
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.memorize_config = self._validate_config(memorize_config, MemorizeConfig)
        self.retrieve_config = self._validate_config(retrieve_config, RetrieveConfig)
        self.user_config = self._validate_config(user_config, UserConfig)
        self.fs = LocalFS(self.blob_config.resources_dir)

        # Initialize LLM client
        self.llm_client: Any = self._init_llm_client()
        # Initialize embedding client
        self.embedding_client: Any = self._init_embedding_client()

        self.category_configs: list[dict[str, str]] = list(self.memorize_config.memory_categories or [])
        self._category_prompt_str = self._format_categories_for_prompt(self.category_configs)
        self._contexts: dict[str | None, _UserContext] = {}
        default_context = self._create_context()
        self._contexts[None] = default_context
        self.store = default_context.store
        self._start_category_initialization(default_context)

    def user(self, **user_data: Any) -> MemoryUser:
        """
        Get or create a MemoryUser scoped instance using the configured user model.

        Args:
            **user_data: Fields passed to the configured user model (e.g., user_id).

        Returns:
            MemoryUser bound to this service configuration.
        """
        user_model = self.user_config.model(**user_data)
        memory_user = MemoryUser(service=self, user=user_model)

        return memory_user

    def _create_context(self) -> _UserContext:
        return _UserContext(categories_ready=not bool(self.category_configs))

    def _context_key(self, user: BaseModel | None) -> str | None:
        if user is None:
            return None
        user_id = getattr(user, "user_id", None)
        if user_id is not None:
            return f"{user.__class__.__name__}:{user_id}"
        try:
            return json.dumps(user.model_dump(), sort_keys=True)
        except Exception:
            return str(user)

    def _get_user_context(self, user: BaseModel | None) -> _UserContext:
        key = self._context_key(user)
        ctx = self._contexts.get(key)
        if ctx:
            return ctx
        ctx = self._create_context()
        self._contexts[key] = ctx
        self._start_category_initialization(ctx)
        return ctx

    def _init_llm_client(self) -> Any:
        """Initialize LLM client based on configuration."""
        backend = self.llm_config.client_backend
        if backend == "sdk":
            from memu.llm.openai_sdk import OpenAISDKClient

            return OpenAISDKClient(
                base_url=self.llm_config.base_url,
                api_key=self.llm_config.api_key,
                chat_model=self.llm_config.chat_model,
            )
        elif backend == "httpx":
            return HTTPLLMClient(
                base_url=self.llm_config.base_url,
                api_key=self.llm_config.api_key,
                chat_model=self.llm_config.chat_model,
                provider=self.llm_config.provider,
                endpoint_overrides=self.llm_config.endpoint_overrides,
            )
        else:
            msg = f"Unknown llm_client_backend '{self.llm_config.client_backend}'"
            raise ValueError(msg)

    def _init_embedding_client(self) -> Any:
        """Initialize embedding client based on configuration."""
        backend = self.embedding_config.client_backend
        if backend == "sdk":
            from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient

            return OpenAIEmbeddingSDKClient(
                base_url=self.embedding_config.base_url,
                api_key=self.embedding_config.api_key,
                embed_model=self.embedding_config.embed_model,
                batch_size=self.embedding_config.batch_size,
            )
        elif backend == "httpx":
            return HTTPEmbeddingClient(
                base_url=self.embedding_config.base_url,
                api_key=self.embedding_config.api_key,
                embed_model=self.embedding_config.embed_model,
                provider=self.embedding_config.provider,
                endpoint_overrides=self.embedding_config.endpoint_overrides,
            )
        else:
            msg = f"Unknown embedding_client_backend '{self.embedding_config.client_backend}'"
            raise ValueError(msg)

    async def memorize(
        self,
        *,
        resource_url: str,
        modality: str,
        summary_prompt: str | None = None,
        user: BaseModel | None = None,
    ) -> dict[str, Any]:
        ctx = self._get_user_context(user)
        local_path, preprocessed_resources = await self._fetch_and_preprocess_resource(resource_url, modality)

        await self._ensure_categories_ready(ctx)
        cat_ids: list[str] = list(ctx.category_ids)

        memory_types = self._resolve_memory_types()
        base_prompt = self._resolve_summary_prompt(modality, summary_prompt)
        categories_prompt_str = self._category_prompt_str

        all_resources: list[Resource] = []
        all_items: list[Any] = []
        all_rels: list[Any] = []
        all_category_updates: dict[str, list[Any]] = {}

        # Process each preprocessed resource (single for most modalities, multiple for conversations)
        for idx, prep_resource in enumerate(preprocessed_resources):
            text = prep_resource.get("text")
            caption = prep_resource.get("caption")

            # Create resource URL (append segment index if multiple)
            if len(preprocessed_resources) > 1:
                # Format: filename_#segment_N.ext
                path = pathlib.Path(resource_url)
                res_url = f"{path.stem}_#segment_{idx}{path.suffix}"
            else:
                res_url = resource_url

            # Create resource with caption
            res = await self._create_resource_with_caption(
                resource_url=res_url,
                modality=modality,
                local_path=local_path,
                caption=caption,
                ctx=ctx,
            )
            all_resources.append(res)

            # Generate entries for this resource
            structured_entries = await self._generate_structured_entries(
                resource_url=res_url,
                modality=modality,
                memory_types=memory_types,
                text=text,
                base_prompt=base_prompt,
                categories_prompt_str=categories_prompt_str,
            )

            if not structured_entries:
                continue

            items, rels, category_memory_updates = await self._persist_memory_items(
                resource_id=res.id,
                structured_entries=structured_entries,
                ctx=ctx,
            )

            all_items.extend(items)
            all_rels.extend(rels)
            for cat_id, mem_items in category_memory_updates.items():
                all_category_updates.setdefault(cat_id, []).extend(mem_items)

        await self._update_category_summaries(all_category_updates, ctx=ctx)

        # Return format depends on number of resources
        if len(all_resources) == 1:
            return {
                "resource": self._model_dump_without_embeddings(all_resources[0]),
                "items": [self._model_dump_without_embeddings(item) for item in all_items],
                "categories": [self._model_dump_without_embeddings(ctx.store.categories[c]) for c in cat_ids],
                "relations": [r.model_dump() for r in all_rels],
            }
        else:
            return {
                "resources": [self._model_dump_without_embeddings(r) for r in all_resources],
                "items": [self._model_dump_without_embeddings(item) for item in all_items],
                "categories": [self._model_dump_without_embeddings(ctx.store.categories[c]) for c in cat_ids],
                "relations": [r.model_dump() for r in all_rels],
            }

    async def _fetch_and_preprocess_resource(
        self, resource_url: str, modality: str
    ) -> tuple[str, list[dict[str, str | None]]]:
        """
        Fetch and preprocess a resource.

        Returns:
            Tuple of (local_path, preprocessed_resources)
            where preprocessed_resources is a list of dicts with 'text' and 'caption'
        """
        local_path, text = await self.fs.fetch(resource_url, modality)
        preprocessed_resources = await self._preprocess_resource_url(
            local_path=local_path, text=text, modality=modality
        )
        return local_path, preprocessed_resources

    async def _create_resource_with_caption(
        self,
        *,
        resource_url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        ctx: _UserContext,
    ) -> Resource:
        res = ctx.store.create_resource(url=resource_url, modality=modality, local_path=local_path)
        if caption:
            caption_text = caption.strip()
            if caption_text:
                res.caption = caption_text
                res.embedding = (await self.embedding_client.embed([caption_text]))[0]
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
        segments: list[dict[str, int | str]] | None = None,
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
        segments: list[dict[str, int | str]] | None,
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
        segments: list[dict[str, int | str]],
        memory_types: list[MemoryType],
        base_prompt: str,
        categories_prompt_str: str,
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
        tasks = [self.llm_client.summarize(prompt_text, system_prompt=base_prompt) for prompt_text in prompts]
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
        self,
        *,
        resource_id: str,
        structured_entries: list[tuple[MemoryType, str, list[str]]],
        ctx: _UserContext,
    ) -> tuple[list[MemoryItem], list[CategoryItem], dict[str, list[str]]]:
        summary_payloads = [content for _, content, _ in structured_entries]
        item_embeddings = await self.embedding_client.embed(summary_payloads) if summary_payloads else []
        items: list[MemoryItem] = []
        rels: list[CategoryItem] = []
        category_memory_updates: dict[str, list[str]] = {}

        for (memory_type, summary_text, cat_names), emb in zip(structured_entries, item_embeddings, strict=True):
            item = ctx.store.create_item(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary_text,
                embedding=emb,
            )
            items.append(item)
            mapped_cat_ids = self._map_category_names_to_ids(cat_names, ctx)
            for cid in mapped_cat_ids:
                rels.append(ctx.store.link_item_category(item.id, cid))
                category_memory_updates.setdefault(cid, []).append(summary_text)

        return items, rels, category_memory_updates

    def _start_category_initialization(self, ctx: _UserContext) -> None:
        if ctx.categories_ready:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop:
            ctx.category_init_task = loop.create_task(self._initialize_categories(ctx))
        else:
            asyncio.run(self._initialize_categories(ctx))

    async def _ensure_categories_ready(self, ctx: _UserContext) -> None:
        if ctx.categories_ready:
            return
        if ctx.category_init_task:
            await ctx.category_init_task
            ctx.category_init_task = None
            return
        await self._initialize_categories(ctx)

    async def _initialize_categories(self, ctx: _UserContext) -> None:
        if ctx.categories_ready:
            return
        if not self.category_configs:
            ctx.categories_ready = True
            return
        cat_texts = [self._category_embedding_text(cfg) for cfg in self.category_configs]
        cat_vecs = await self.embedding_client.embed(cat_texts)
        ctx.category_ids = []
        ctx.category_name_to_id = {}
        for cfg, vec in zip(self.category_configs, cat_vecs, strict=True):
            name = (cfg.get("name") or "").strip() or "Untitled"
            description = (cfg.get("description") or "").strip()
            cat = ctx.store.get_or_create_category(name=name, description=description, embedding=vec)
            ctx.category_ids.append(cat.id)
            ctx.category_name_to_id[name.lower()] = cat.id
        ctx.categories_ready = True

    @staticmethod
    def _category_embedding_text(cat: dict[str, str]) -> str:
        name = (cat.get("name") or "").strip() or "Untitled"
        desc = (cat.get("description") or "").strip()
        return f"{name}: {desc}" if desc else name

    def _map_category_names_to_ids(self, names: list[str], ctx: _UserContext) -> list[str]:
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

    async def _preprocess_resource_url(
        self, *, local_path: str, text: str | None, modality: str
    ) -> list[dict[str, str | None]]:
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
            List of preprocessed resources, each with 'text' and 'caption'
        """
        template = PREPROCESS_PROMPTS.get(modality)
        if not template:
            return [{"text": text, "caption": None}]

        if modality == "audio":
            text = await self._prepare_audio_text(local_path, text)
            if text is None:
                return [{"text": None, "caption": None}]

        if self._modality_requires_text(modality) and not text:
            return [{"text": text, "caption": None}]

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
                transcribed = cast(str, await self.llm_client.transcribe(local_path))
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
    ) -> list[dict[str, str | None]]:
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
        return [{"text": text, "caption": None}]

    async def _preprocess_conversation(self, text: str, template: str) -> list[dict[str, str | None]]:
        """Preprocess conversation data with segmentation, returns list of resources (one per segment)."""
        preprocessed_text = format_conversation_for_preprocess(text)
        prompt = template.format(conversation=self._escape_prompt_value(preprocessed_text))
        processed = await self.llm_client.summarize(prompt, system_prompt=None)
        _conv, segments = self._parse_conversation_preprocess_with_segments(processed, preprocessed_text)

        # Important: always use the original JSON-derived, indexed conversation text for downstream
        # segmentation and memory extraction. The LLM may rewrite the conversation and drop fields
        # like created_at, which would cause them to be lost.
        conversation_text = preprocessed_text
        # If no segments, return single resource
        if not segments:
            return [{"text": conversation_text, "caption": None}]

        # Generate caption for each segment and return as separate resources
        lines = conversation_text.split("\n")
        max_idx = len(lines) - 1
        resources: list[dict[str, str | None]] = []

        for segment in segments:
            start = int(segment.get("start", 0))
            end = int(segment.get("end", max_idx))
            start = max(0, min(start, max_idx))
            end = max(0, min(end, max_idx))
            segment_text = "\n".join(lines[start : end + 1])

            if segment_text.strip():
                caption = await self._summarize_segment(segment_text)
                resources.append({"text": segment_text, "caption": caption})
        return resources if resources else [{"text": conversation_text, "caption": None}]

    async def _summarize_segment(self, segment_text: str) -> str | None:
        """Summarize a single conversation segment."""
        prompt = f"""Summarize the following conversation segment in 1-2 concise sentences.
Focus on the main topic or theme discussed.

Conversation:
{segment_text}

Summary:"""
        try:
            response = await self.llm_client.summarize(prompt, system_prompt=None)
            return response.strip() if response else None
        except Exception:
            logger.exception("Failed to summarize segment")
            return None

    async def _preprocess_video(self, local_path: str, template: str) -> list[dict[str, str | None]]:
        """
        Preprocess video data - extract description and caption using Vision API.

        Extracts the middle frame from the video and analyzes it using Vision API.

        Args:
            local_path: Path to the video file
            template: Prompt template for video analysis

        Returns:
            List with single resource containing text (description) and caption
        """
        try:
            # Check if ffmpeg is available
            if not VideoFrameExtractor.is_ffmpeg_available():
                logger.warning("ffmpeg not available, cannot process video. Returning None.")
                return [{"text": None, "caption": None}]

            # Extract middle frame from video
            logger.info(f"Extracting frame from video: {local_path}")
            frame_path = VideoFrameExtractor.extract_middle_frame(local_path)

            try:
                # Call Vision API with extracted frame
                logger.info(f"Analyzing video frame with Vision API: {frame_path}")
                processed = await self.llm_client.vision(prompt=template, image_path=frame_path, system_prompt=None)
                description, caption = self._parse_multimodal_response(processed, "detailed_description", "caption")
                return [{"text": description, "caption": caption}]
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
            return [{"text": None, "caption": None}]

    async def _preprocess_image(self, local_path: str, template: str) -> list[dict[str, str | None]]:
        """
        Preprocess image data - extract description and caption using Vision API.

        Args:
            local_path: Path to the image file
            template: Prompt template for image analysis

        Returns:
            List with single resource containing text (description) and caption
        """
        # Call Vision API with image
        processed = await self.llm_client.vision(prompt=template, image_path=local_path, system_prompt=None)
        description, caption = self._parse_multimodal_response(processed, "detailed_description", "caption")
        return [{"text": description, "caption": caption}]

    async def _preprocess_document(self, text: str, template: str) -> list[dict[str, str | None]]:
        """Preprocess document data - condense and extract caption"""
        prompt = template.format(document_text=self._escape_prompt_value(text))
        processed = await self.llm_client.summarize(prompt, system_prompt=None)
        processed_content, caption = self._parse_multimodal_response(processed, "processed_content", "caption")
        return [{"text": processed_content or text, "caption": caption}]

    async def _preprocess_audio(self, text: str, template: str) -> list[dict[str, str | None]]:
        """Preprocess audio data - format transcription and extract caption"""
        prompt = template.format(transcription=self._escape_prompt_value(text))
        processed = await self.llm_client.summarize(prompt, system_prompt=None)
        processed_content, caption = self._parse_multimodal_response(processed, "processed_content", "caption")
        return [{"text": processed_content or text, "caption": caption}]

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

    async def _update_category_summaries(self, updates: dict[str, list[str]], ctx: _UserContext) -> None:
        if not updates:
            return
        tasks = []
        target_ids: list[str] = []
        for cid, memories in updates.items():
            cat = ctx.store.categories.get(cid)
            if not cat or not memories:
                continue
            prompt = self._build_category_summary_prompt(category=cat, new_memories=memories)
            tasks.append(self.llm_client.summarize(prompt, system_prompt=None))
            target_ids.append(cid)
        if not tasks:
            return
        summaries = await asyncio.gather(*tasks)
        for cid, summary in zip(target_ids, summaries, strict=True):
            cat = ctx.store.categories.get(cid)
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
    ) -> tuple[str | None, list[dict[str, int | str]] | None]:
        """
        Parse conversation preprocess response and extract segments.
        Returns: (conversation_text, segments)
        """
        conversation = self._extract_tag_content(raw, "conversation")
        segments = self._extract_segments_with_fallback(raw)
        return conversation, segments

    def _extract_segments_with_fallback(self, raw: str) -> list[dict[str, int | str]] | None:
        segments = self._segments_from_json_payload(raw)
        if segments is not None:
            return segments
        try:
            blob = self._extract_json_blob(raw)
        except Exception:
            logging.exception("Failed to extract segments from conversation preprocess response")
            return None
        return self._segments_from_json_payload(blob)

    def _segments_from_json_payload(self, payload: str) -> list[dict[str, int | str]] | None:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError, TypeError:
            return None
        return self._segments_from_parsed_data(parsed)

    @staticmethod
    def _segments_from_parsed_data(parsed: Any) -> list[dict[str, int | str]] | None:
        if not isinstance(parsed, dict):
            return None
        segments_data = parsed.get("segments")
        if not isinstance(segments_data, list):
            return None
        segments: list[dict[str, int | str]] = []
        for seg in segments_data:
            if isinstance(seg, dict) and "start" in seg and "end" in seg:
                try:
                    segment: dict[str, int | str] = {
                        "start": int(seg["start"]),
                        "end": int(seg["end"]),
                    }
                    if "caption" in seg and isinstance(seg["caption"], str):
                        segment["caption"] = seg["caption"]
                    segments.append(segment)
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
        user: BaseModel | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve relevant memories based on the query using either RAG-based or LLM-based search.

        Args:
            queries: List of query messages in format [{"role": "user", "content": {"text": "..."}}].
                     The last one is the current query, others are context.
                     If list has only 1 element, no query rewriting is performed.
            user: Optional user object to scope retrieval to that user's memories.

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
        ctx = self._get_user_context(user)
        await self._ensure_categories_ready(ctx)

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
                rewritten_query,
                top_k=self.retrieve_config.top_k,
                context_queries=context_queries_objs,
                ctx=ctx,
            )
        else:  # rag
            results = await self._embedding_based_retrieve(
                rewritten_query,
                top_k=self.retrieve_config.top_k,
                context_queries=context_queries_objs,
                ctx=ctx,
            )

        # Add metadata
        results["needs_retrieval"] = True
        results["original_query"] = current_query
        results["rewritten_query"] = rewritten_query
        if "next_step_query" not in results:
            results["next_step_query"] = None

        return results

    async def _rank_categories_by_summary(
        self, query_vec: list[float], top_k: int, ctx: _UserContext
    ) -> tuple[list[tuple[str, float]], dict[str, str]]:
        entries = [(cid, cat.summary) for cid, cat in ctx.store.categories.items() if cat.summary]
        if not entries:
            return [], {}
        summary_texts = [summary for _, summary in entries]
        summary_embeddings = await self.embedding_client.embed(summary_texts)
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
        response = await self.llm_client.summarize(prompt, system_prompt=sys_prompt)
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
        self, query: str, top_k: int, context_queries: list[dict[str, Any]] | None, ctx: _UserContext
    ) -> dict[str, Any]:
        """Embedding-based retrieval with query rewriting and judging at each tier"""
        current_query = query
        qvec = (await self.embedding_client.embed([current_query]))[0]
        response: dict[str, Any] = {"resources": [], "items": [], "categories": [], "next_step_query": None}
        content_sections: list[str] = []

        # Tier 1: Categories
        cat_hits, summary_lookup = await self._rank_categories_by_summary(qvec, top_k, ctx)
        if cat_hits:
            response["categories"] = self._materialize_hits(cat_hits, ctx.store.categories)
            content_sections.append(self._format_category_content(cat_hits, summary_lookup, ctx.store))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query, context_queries, retrieved_content="\n\n".join(content_sections)
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response
            # Re-embed with rewritten query
            qvec = (await self.embedding_client.embed([current_query]))[0]

        # Tier 2: Items
        item_hits = cosine_topk(qvec, [(i.id, i.embedding) for i in ctx.store.items.values()], k=top_k)
        if item_hits:
            response["items"] = self._materialize_hits(item_hits, ctx.store.items)
            content_sections.append(self._format_item_content(item_hits, ctx.store))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query, context_queries, retrieved_content="\n\n".join(content_sections)
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response
            # Re-embed with rewritten query
            qvec = (await self.embedding_client.embed([current_query]))[0]

        # Tier 3: Resources
        resource_corpus = self._resource_caption_corpus(ctx.store)
        if resource_corpus:
            res_hits = cosine_topk(qvec, resource_corpus, k=top_k)
            if res_hits:
                response["resources"] = self._materialize_hits(res_hits, ctx.store.resources)
                content_sections.append(self._format_resource_content(res_hits, ctx.store))

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

    def _format_category_content(
        self, hits: list[tuple[str, float]], summaries: dict[str, str], store: InMemoryStore
    ) -> str:
        lines = []
        for cid, score in hits:
            cat = store.categories.get(cid)
            if not cat:
                continue
            summary = summaries.get(cid) or cat.summary or ""
            lines.append(f"Category: {cat.name}\nSummary: {summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_item_content(self, hits: list[tuple[str, float]], store: InMemoryStore) -> str:
        lines = []
        for iid, score in hits:
            item = store.items.get(iid)
            if not item:
                continue
            lines.append(f"Memory Item ({item.memory_type}): {item.summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_resource_content(self, hits: list[tuple[str, float]], store: InMemoryStore) -> str:
        lines = []
        for rid, score in hits:
            res = store.resources.get(rid)
            if not res:
                continue
            caption = res.caption or f"Resource {res.url}"
            lines.append(f"Resource: {caption}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _resource_caption_corpus(self, store: InMemoryStore) -> list[tuple[str, list[float]]]:
        corpus: list[tuple[str, list[float]]] = []
        for rid, res in store.resources.items():
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
        self, query: str, top_k: int, context_queries: list[dict[str, Any]] | None, ctx: _UserContext
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
        category_hits = await self._llm_rank_categories(current_query, top_k, ctx)
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
        item_hits = await self._llm_rank_items(current_query, top_k, relevant_category_ids, category_hits, ctx)
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
        resource_hits = await self._llm_rank_resources(current_query, top_k, category_hits, item_hits, ctx)
        if resource_hits:
            response["resources"] = resource_hits
            content_sections.append(self._format_llm_resource_content(resource_hits))

        return response

    def _format_categories_for_llm(self, store: InMemoryStore, category_ids: list[str] | None = None) -> str:
        """Format categories for LLM consumption"""
        categories_to_format = store.categories
        if category_ids:
            categories_to_format = {cid: cat for cid, cat in store.categories.items() if cid in category_ids}

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

    def _format_items_for_llm(self, store: InMemoryStore, category_ids: list[str] | None = None) -> str:
        """Format memory items for LLM consumption, optionally filtered by category"""
        items_to_format = []
        seen_item_ids = set()

        if category_ids:
            # Get items that belong to the specified categories
            for rel in store.relations:
                if rel.category_id in category_ids:
                    item = store.items.get(rel.item_id)
                    if item and item.id not in seen_item_ids:
                        items_to_format.append(item)
                        seen_item_ids.add(item.id)
        else:
            items_to_format = list(store.items.values())

        if not items_to_format:
            return "No memory items available."

        lines = []
        for item in items_to_format:
            lines.append(f"ID: {item.id}")
            lines.append(f"Type: {item.memory_type}")
            lines.append(f"Summary: {item.summary}")
            lines.append("---")

        return "\n".join(lines)

    def _format_resources_for_llm(self, store: InMemoryStore, item_ids: list[str] | None = None) -> str:
        """Format resources for LLM consumption, optionally filtered by related items"""
        resources_to_format = []

        if item_ids:
            # Get resources that are related to the specified items
            resource_ids = {store.items[iid].resource_id for iid in item_ids if iid in store.items}
            resources_to_format = [store.resources[rid] for rid in resource_ids if rid in store.resources]
        else:
            resources_to_format = list(store.resources.values())

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

    async def _llm_rank_categories(self, query: str, top_k: int, ctx: _UserContext) -> list[dict[str, Any]]:
        """Use LLM to rank categories based on query relevance"""
        if not ctx.store.categories:
            return []

        categories_data = self._format_categories_for_llm(ctx.store)
        prompt = LLM_CATEGORY_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            categories_data=self._escape_prompt_value(categories_data),
        )

        llm_response = await self.llm_client.summarize(prompt, system_prompt=None)
        return self._parse_llm_category_response(llm_response, ctx.store)

    async def _llm_rank_items(
        self,
        query: str,
        top_k: int,
        category_ids: list[str],
        category_hits: list[dict[str, Any]],
        ctx: _UserContext,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank memory items from relevant categories"""
        if not category_ids:
            print("[LLM Rank Items] No category_ids provided")
            return []

        items_data = self._format_items_for_llm(ctx.store, category_ids)
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

        llm_response = await self.llm_client.summarize(prompt, system_prompt=None)
        return self._parse_llm_item_response(llm_response, ctx.store)

    async def _llm_rank_resources(
        self,
        query: str,
        top_k: int,
        category_hits: list[dict[str, Any]],
        item_hits: list[dict[str, Any]],
        ctx: _UserContext,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank resources related to the context"""
        # Get item IDs to filter resources
        item_ids = [item["id"] for item in item_hits]
        if not item_ids:
            return []

        resources_data = self._format_resources_for_llm(ctx.store, item_ids)
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

        llm_response = await self.llm_client.summarize(prompt, system_prompt=None)
        return self._parse_llm_resource_response(llm_response, ctx.store)

    def _parse_llm_category_response(self, raw_response: str, store: InMemoryStore) -> list[dict[str, Any]]:
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
                        cat = store.categories.get(cat_id)
                        if cat:
                            cat_data = self._model_dump_without_embeddings(cat)
                            results.append(cat_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM category ranking response: {e}")

        return results

    def _parse_llm_item_response(self, raw_response: str, store: InMemoryStore) -> list[dict[str, Any]]:
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
                        mem_item = store.items.get(item_id)
                        if mem_item:
                            item_data = self._model_dump_without_embeddings(mem_item)
                            results.append(item_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM item ranking response: {e}")

        return results

    def _parse_llm_resource_response(self, raw_response: str, store: InMemoryStore) -> list[dict[str, Any]]:
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
                        res = store.resources.get(res_id)
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


class MemoryUser:
    """
    User-scoped memory service that reuses the parent service's clients/config
    but maintains an isolated in-memory store and category state.
    """

    def __init__(self, *, service: MemoryService, user: BaseModel):
        # Reuse core dependencies from the parent service
        self.user = user
        self.service = service

    async def memorize(self, *, resource_url: str, modality: str, summary_prompt: str | None = None) -> dict[str, Any]:
        return await self.service.memorize(
            resource_url=resource_url,
            modality=modality,
            summary_prompt=summary_prompt,
            user=self.user,
        )

    async def retrieve(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        return await self.service.retrieve(queries=queries, user=self.user)
