from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from memu.app.crud import CRUDMixin
from memu.app.memorize import MemorizeMixin
from memu.app.retrieve import RetrieveMixin
from memu.app.settings import (
    BlobConfig,
    CategoryConfig,
    DatabaseConfig,
    EmbeddingConfig,
    EmbeddingProfilesConfig,
    LLMConfig,
    LLMProfilesConfig,
    MemorizeConfig,
    MemoryFilesConfig,
    RetrieveConfig,
    UserConfig,
    VLMConfig,
    embedding_config_from_llm,
    vlm_config_from_llm,
)
from memu.blob.local_fs import LocalFS
from memu.database.factory import build_database
from memu.database.interfaces import Database
from memu.embedding.gateway import build_embedding_client
from memu.llm.gateway import build_llm_client
from memu.llm.wrapper import (
    LLMCallMetadata,
    LLMClientWrapper,
    LLMInterceptorHandle,
    LLMInterceptorRegistry,
)
from memu.memory_fs import ExportResult, MemoryFileExporter, MemorySynthesizer
from memu.vlm.gateway import build_vlm_client
from memu.workflow.interceptor import WorkflowInterceptorHandle, WorkflowInterceptorRegistry
from memu.workflow.pipeline import PipelineManager
from memu.workflow.runner import WorkflowRunner, resolve_workflow_runner
from memu.workflow.step import WorkflowState, WorkflowStep

TConfigModel = TypeVar("TConfigModel", bound=BaseModel)


@dataclass
class Context:
    categories_ready: bool = False
    category_ids: list[str] = field(default_factory=list)
    category_name_to_id: dict[str, str] = field(default_factory=dict)
    category_init_task: asyncio.Task | None = None


class MemoryService(MemorizeMixin, RetrieveMixin, CRUDMixin):
    def __init__(
        self,
        *,
        llm_profiles: LLMProfilesConfig | dict[str, Any] | None = None,
        blob_config: BlobConfig | dict[str, Any] | None = None,
        database_config: DatabaseConfig | dict[str, Any] | None = None,
        memorize_config: MemorizeConfig | dict[str, Any] | None = None,
        retrieve_config: RetrieveConfig | dict[str, Any] | None = None,
        workflow_runner: WorkflowRunner | str | None = None,
        user_config: UserConfig | dict[str, Any] | None = None,
        memory_files_config: MemoryFilesConfig | dict[str, Any] | None = None,
        embedding_profiles: EmbeddingProfilesConfig | dict[str, Any] | None = None,
    ):
        self.llm_profiles = self._validate_config(llm_profiles, LLMProfilesConfig)
        self.user_config = self._validate_config(user_config, UserConfig)
        self.user_model = self.user_config.model
        self.llm_config = self._validate_config(self.llm_profiles.default, LLMConfig)
        self.blob_config = self._validate_config(blob_config, BlobConfig)
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.memorize_config = self._validate_config(memorize_config, MemorizeConfig)
        self.retrieve_config = self._validate_config(retrieve_config, RetrieveConfig)
        self.memory_files_config = self._validate_config(memory_files_config, MemoryFilesConfig)

        self.fs = LocalFS(self.blob_config.resources_dir)
        self.category_configs: list[CategoryConfig] = list(self.memorize_config.memory_categories or [])
        self.category_config_map: dict[str, CategoryConfig] = {cfg.name: cfg for cfg in self.category_configs}
        self._category_prompt_str = self._format_categories_for_prompt(self.category_configs)

        self._context = Context(categories_ready=not bool(self.category_configs))

        self.database: Database = build_database(
            config=self.database_config,
            user_model=self.user_model,
        )
        # We need the concrete user scope (user_id: xxx) to initialize the categories
        # self._start_category_initialization(self._context, self.database)

        # VLM (vision-language) profiles are derived from the LLM profiles so
        # image/video vision reuses the same provider/credentials with a stronger
        # multimodal model (see ``vlm_config_from_llm``).
        self.vlm_profiles: dict[str, VLMConfig] = {
            name: vlm_config_from_llm(cfg) for name, cfg in self.llm_profiles.profiles.items()
        }

        # Embedding profiles: use explicit profiles when supplied (e.g. to point
        # vectorization at a dedicated provider such as jina/voyage), otherwise
        # derive them from the LLM profiles so existing configs keep working.
        if embedding_profiles is None:
            self.embedding_profiles: dict[str, EmbeddingConfig] = {
                name: embedding_config_from_llm(cfg) for name, cfg in self.llm_profiles.profiles.items()
            }
        else:
            self.embedding_profiles = self._validate_config(embedding_profiles, EmbeddingProfilesConfig).profiles

        # Initialize client caches (lazy creation on first use)
        self._llm_clients: dict[str, Any] = {}
        self._vlm_clients: dict[str, Any] = {}
        self._embedding_clients: dict[str, Any] = {}
        self._llm_interceptors = LLMInterceptorRegistry()
        self._workflow_interceptors = WorkflowInterceptorRegistry()

        self._workflow_runner = resolve_workflow_runner(workflow_runner)

        # Optional markdown "memory file system" artifact layer (additive, read-only).
        # Writes are serialized through a single lock so concurrent exports never
        # interleave on the shared output directory.
        self._memory_file_exporter = MemoryFileExporter(self.memory_files_config.output_dir)
        self._memory_synthesizer = MemorySynthesizer()
        self._memory_files_lock = asyncio.Lock()

        self._pipelines = PipelineManager(
            available_capabilities={"llm", "vector", "db", "io", "vision"},
            llm_profiles=set(self.llm_profiles.profiles.keys()),
        )
        self._register_pipelines()

    def _init_llm_client(self, config: LLMConfig | None = None) -> Any:
        """Initialize LLM client based on configuration via the LLM gateway."""
        cfg = config or self.llm_config
        return build_llm_client(cfg)

    def _get_llm_base_client(self, profile: str | None = None) -> Any:
        """
        Lazily initialize and cache LLM clients per profile to avoid eager network setup.
        """
        name = profile or "default"
        client = self._llm_clients.get(name)
        if client is not None:
            return client
        cfg: LLMConfig | None = self.llm_profiles.profiles.get(name)
        if cfg is None:
            msg = f"Unknown llm profile '{name}'"
            raise KeyError(msg)
        client = self._init_llm_client(cfg)
        self._llm_clients[name] = client
        return client

    @staticmethod
    def _llm_call_metadata(profile: str, step_context: Mapping[str, Any] | None) -> LLMCallMetadata:
        if not isinstance(step_context, Mapping):
            return LLMCallMetadata(profile)
        operation = None
        for key in ("operation", "workflow_name"):
            value = step_context.get(key)
            if isinstance(value, str) and value.strip():
                operation = value.strip()
                break
        step_id = step_context.get("step_id") if isinstance(step_context.get("step_id"), str) else None
        trace_id = step_context.get("trace_id") if isinstance(step_context.get("trace_id"), str) else None
        tags = step_context.get("tags") if isinstance(step_context.get("tags"), Mapping) else None
        return LLMCallMetadata(profile=profile, operation=operation, step_id=step_id, trace_id=trace_id, tags=tags)

    def _wrap_llm_client(
        self,
        client: Any,
        *,
        profile: str | None = None,
        step_context: Mapping[str, Any] | None = None,
    ) -> Any:
        cfg: LLMConfig | None = self.llm_profiles.profiles.get(profile or "default")
        provider = cfg.provider if cfg is not None else None
        metadata = self._llm_call_metadata(profile or "default", step_context)
        return LLMClientWrapper(
            client,
            registry=self._llm_interceptors,
            metadata=metadata,
            provider=provider,
            chat_model=getattr(client, "chat_model", None),
        )

    def _get_llm_client(self, profile: str | None = None, step_context: Mapping[str, Any] | None = None) -> Any:
        base_client = self._get_llm_base_client(profile)
        return self._wrap_llm_client(base_client, profile=profile, step_context=step_context)

    def _get_vlm_base_client(self, profile: str | None = None) -> Any:
        """Lazily initialize and cache VLM clients per profile."""
        name = profile or "default"
        client = self._vlm_clients.get(name)
        if client is not None:
            return client
        cfg: VLMConfig | None = self.vlm_profiles.get(name)
        if cfg is None:
            msg = f"Unknown vlm profile '{name}'"
            raise KeyError(msg)
        client = build_vlm_client(cfg)
        self._vlm_clients[name] = client
        return client

    def _get_vlm_client(self, profile: str | None = None, step_context: Mapping[str, Any] | None = None) -> Any:
        base_client = self._get_vlm_base_client(profile)
        cfg = self.vlm_profiles.get(profile or "default")
        provider = cfg.provider if cfg is not None else None
        metadata = self._llm_call_metadata(profile or "default", step_context)
        return LLMClientWrapper(
            base_client,
            registry=self._llm_interceptors,
            metadata=metadata,
            provider=provider,
            chat_model=getattr(base_client, "vlm_model", None),
        )

    def _get_embedding_base_client(self, profile: str | None = None) -> Any:
        """Lazily initialize and cache embedding clients per profile."""
        name = profile or "default"
        client = self._embedding_clients.get(name)
        if client is not None:
            return client
        cfg: EmbeddingConfig | None = self.embedding_profiles.get(name)
        if cfg is None:
            msg = f"Unknown embedding profile '{name}'"
            raise KeyError(msg)
        client = build_embedding_client(cfg)
        self._embedding_clients[name] = client
        return client

    def _get_embedding_client(self, profile: str | None = None, step_context: Mapping[str, Any] | None = None) -> Any:
        base_client = self._get_embedding_base_client(profile)
        cfg = self.embedding_profiles.get(profile or "default")
        provider = cfg.provider if cfg is not None else None
        metadata = self._llm_call_metadata(profile or "default", step_context)
        return LLMClientWrapper(
            base_client,
            registry=self._llm_interceptors,
            metadata=metadata,
            provider=provider,
            embed_model=getattr(base_client, "embed_model", None),
        )

    @property
    def llm_client(self) -> Any:
        """Default LLM client (lazy)."""
        return self._get_llm_client()

    @property
    def workflow_runner(self) -> WorkflowRunner:
        """Current workflow runner backend."""
        return self._workflow_runner

    @staticmethod
    def _llm_profile_from_context(
        step_context: Mapping[str, Any] | None, task: Literal["chat", "embedding"] = "chat"
    ) -> str | None:
        if not isinstance(step_context, Mapping):
            return None
        step_cfg = step_context.get("step_config")
        if not isinstance(step_cfg, Mapping):
            return None
        if task == "chat":
            profile = step_cfg.get("chat_llm_profile", step_cfg.get("llm_profile"))
        elif task == "embedding":
            profile = step_cfg.get("embed_llm_profile", step_cfg.get("llm_profile"))
        else:
            raise ValueError(task)
        if isinstance(profile, str) and profile.strip():
            return profile.strip()
        return None

    def _get_step_llm_client(self, step_context: Mapping[str, Any] | None) -> Any:
        profile = self._llm_profile_from_context(step_context, task="chat") or "default"
        return self._get_llm_client(profile, step_context=step_context)

    def _get_step_embedding_client(self, step_context: Mapping[str, Any] | None) -> Any:
        profile = self._llm_profile_from_context(step_context, task="embedding") or "embedding"
        return self._get_embedding_client(profile, step_context=step_context)

    def intercept_before_llm_call(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        priority: int = 0,
        where: Mapping[str, Any] | Callable[..., Any] | None = None,
    ) -> LLMInterceptorHandle:
        return self._llm_interceptors.register_before(fn, name=name, priority=priority, where=where)

    def intercept_after_llm_call(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        priority: int = 0,
        where: Mapping[str, Any] | Callable[..., Any] | None = None,
    ) -> LLMInterceptorHandle:
        return self._llm_interceptors.register_after(fn, name=name, priority=priority, where=where)

    def intercept_on_error_llm_call(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        priority: int = 0,
        where: Mapping[str, Any] | Callable[..., Any] | None = None,
    ) -> LLMInterceptorHandle:
        return self._llm_interceptors.register_on_error(fn, name=name, priority=priority, where=where)

    def intercept_before_workflow_step(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        Register an interceptor to be called before each workflow step.

        The interceptor receives (step_context: WorkflowStepContext, state: WorkflowState).
        """
        return self._workflow_interceptors.register_before(fn, name=name)

    def intercept_after_workflow_step(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        Register an interceptor to be called after each workflow step.

        The interceptor receives (step_context: WorkflowStepContext, state: WorkflowState).
        """
        return self._workflow_interceptors.register_after(fn, name=name)

    def intercept_on_error_workflow_step(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        Register an interceptor to be called when a workflow step raises an exception.

        The interceptor receives (step_context: WorkflowStepContext, state: WorkflowState, error: Exception).
        """
        return self._workflow_interceptors.register_on_error(fn, name=name)

    def _get_context(self) -> Context:
        return self._context

    def _get_database(self) -> Database:
        return self.database

    def _provider_summary(self) -> dict[str, Any]:
        vector_provider = None
        if self.database_config.vector_index:
            vector_provider = self.database_config.vector_index.provider
        return {
            "llm_profiles": list(self.llm_profiles.profiles.keys()),
            "storage": {
                "metadata_store": self.database_config.metadata_store.provider,
                "vector_index": vector_provider,
            },
        }

    def _register_pipelines(self) -> None:
        memo_workflow = self._build_memorize_workflow()
        memo_initial_keys = self._list_memorize_initial_keys()
        self._pipelines.register("memorize", memo_workflow, initial_state_keys=memo_initial_keys)
        rag_workflow = self._build_rag_retrieve_workflow()
        retrieve_initial_keys = self._list_retrieve_initial_keys()
        self._pipelines.register("retrieve_rag", rag_workflow, initial_state_keys=retrieve_initial_keys)
        llm_workflow = self._build_llm_retrieve_workflow()
        self._pipelines.register("retrieve_llm", llm_workflow, initial_state_keys=retrieve_initial_keys)
        patch_create_workflow = self._build_create_memory_item_workflow()
        patch_create_initial_keys = CRUDMixin._list_create_memory_item_initial_keys()
        self._pipelines.register("patch_create", patch_create_workflow, initial_state_keys=patch_create_initial_keys)
        patch_update_workflow = self._build_update_memory_item_workflow()
        patch_update_initial_keys = CRUDMixin._list_update_memory_item_initial_keys()
        self._pipelines.register("patch_update", patch_update_workflow, initial_state_keys=patch_update_initial_keys)
        patch_delete_workflow = self._build_delete_memory_item_workflow()
        patch_delete_initial_keys = CRUDMixin._list_delete_memory_item_initial_keys()
        self._pipelines.register("patch_delete", patch_delete_workflow, initial_state_keys=patch_delete_initial_keys)
        crud_list_items_workflow = self._build_list_memory_items_workflow()
        crud_list_memories_initial_keys = CRUDMixin._list_list_memories_initial_keys()
        self._pipelines.register(
            "crud_list_memory_items", crud_list_items_workflow, initial_state_keys=crud_list_memories_initial_keys
        )
        crud_list_categories_workflow = self._build_list_memory_categories_workflow()
        self._pipelines.register(
            "crud_list_memory_categories",
            crud_list_categories_workflow,
            initial_state_keys=crud_list_memories_initial_keys,
        )
        crud_clear_memory_workflow = self._build_clear_memory_workflow()
        crud_clear_memory_initial_keys = CRUDMixin._list_clear_memories_initial_keys()
        self._pipelines.register(
            "crud_clear_memory", crud_clear_memory_workflow, initial_state_keys=crud_clear_memory_initial_keys
        )

    async def _run_workflow(self, workflow_name: str, initial_state: WorkflowState) -> WorkflowState:
        """Execute a workflow through the configured runner backend."""
        steps = self._pipelines.build(workflow_name)
        runner_context = {"workflow_name": workflow_name}
        return await self._workflow_runner.run(
            workflow_name,
            steps,
            initial_state,
            runner_context,
            interceptor_registry=self._workflow_interceptors,
        )

    async def export_memory_files(self, *, user: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the (optionally scoped) memory store into browsable markdown files.

        Read-only against the database; only artifacts whose rendered content
        changed since the last export are rewritten (diff detection via a sidecar
        manifest). Returns a summary of written/unchanged/removed relative paths.

        Requires ``memory_files_config.enabled=True``.
        """
        if not self.memory_files_config.enabled:
            msg = "Memory files are disabled; set memory_files_config.enabled=True to use export_memory_files()."
            raise RuntimeError(msg)
        where = self.user_model(**user).model_dump() if user is not None else None
        # No changed set => full (re)initialization of the tree.
        return await self._build_memory_files(where, changed=None)

    async def _build_memory_files(
        self,
        where: dict[str, Any] | None,
        *,
        changed: list[Any] | None,
    ) -> dict[str, Any]:
        """Initialize or incrementally update the memory file tree.

        ``changed`` is the list of just-memorized ``Resource`` objects driving an
        incremental update. When it is ``None`` (or no prior tree exists), the tree
        is (re)initialized from the full scoped store.
        """
        memory_body: str | None = None
        skills: dict[str, str] | None = None

        is_update = changed is not None and self._memory_file_exporter.artifacts_exist()

        # The synthesis trunk is the structured store (extracted memory items), not the
        # lossy per-source captions: the just-changed sources for an incremental update,
        # otherwise the full in-scope store for (re)initialization.
        scoped_items = list(self.database.memory_item_repo.list_items(where=where or None).values())
        if is_update:
            changed_resources = list(changed or [])
            changed_ids = {res.id for res in changed_resources}
            changed_items = [item for item in scoped_items if item.resource_id in changed_ids]
            descriptions = MemoryFileExporter.build_synthesis_descriptions(changed_resources, changed_items)
        else:
            resources = list(self.database.resource_repo.list_resources(where=where or None).values())
            descriptions = MemoryFileExporter.build_synthesis_descriptions(resources, scoped_items)

        client = self._get_llm_client(self.memory_files_config.synthesis_llm_profile)

        if self.memory_files_config.synthesize:
            # MEMORY.md and the skill/ tree are both synthesized from descriptions.
            if is_update:
                existing_memory = await asyncio.to_thread(self._memory_file_exporter.read_memory_body)
                existing_skills = await asyncio.to_thread(self._memory_file_exporter.read_skills)
                synthesized = await self._memory_synthesizer.update(
                    descriptions,
                    existing_memory=existing_memory,
                    existing_skills=existing_skills,
                    chat=client.chat,
                )
            else:
                synthesized = await self._memory_synthesizer.synthesize(descriptions, chat=client.chat)
            memory_body, skills = synthesized.memory_body, synthesized.skills
        else:
            # MEMORY.md is rendered deterministically from category summaries, but
            # the skill/ tree is a sibling bypass: always synthesized from the
            # descriptions, never derived from extracted skill-type memory items.
            if is_update:
                existing_skills = await asyncio.to_thread(self._memory_file_exporter.read_skills)
                skills = await self._memory_synthesizer.update_skills(
                    descriptions, existing_skills=existing_skills, chat=client.chat
                )
            else:
                skills = await self._memory_synthesizer.synthesize_skills(descriptions, chat=client.chat)

        async with self._memory_files_lock:
            result: ExportResult = await asyncio.to_thread(
                self._memory_file_exporter.export,
                self.database,
                where=where,
                memory_body=memory_body,
                skills=skills,
            )
        return result.to_dict()

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
        data = obj.model_dump(exclude={"embedding"})
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

    def configure_pipeline(self, *, step_id: str, configs: Mapping[str, Any], pipeline: str = "memorize") -> int:
        revision = self._pipelines.config_step(pipeline, step_id, dict(configs))
        return revision

    def insert_step_after(
        self,
        *,
        target_step_id: str,
        new_step: WorkflowStep,
        pipeline: str = "memorize",
    ) -> int:
        revision = self._pipelines.insert_after(pipeline, target_step_id, new_step)
        return revision

    def insert_step_before(
        self,
        *,
        target_step_id: str,
        new_step: WorkflowStep,
        pipeline: str = "memorize",
    ) -> int:
        revision = self._pipelines.insert_before(pipeline, target_step_id, new_step)
        return revision

    def replace_step(
        self,
        *,
        target_step_id: str,
        new_step: WorkflowStep,
        pipeline: str = "memorize",
    ) -> int:
        revision = self._pipelines.replace_step(pipeline, target_step_id, new_step)
        return revision

    def remove_step(self, *, target_step_id: str, pipeline: str = "memorize") -> int:
        revision = self._pipelines.remove_step(pipeline, target_step_id)
        return revision
