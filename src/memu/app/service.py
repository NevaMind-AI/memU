from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

from memu.app.crud import CRUDMixin
from memu.app.memorize import MemorizeMixin
from memu.app.patch import PatchMixin
from memu.app.retrieve import RetrieveMixin
from memu.app.settings import (
    BlobConfig,
    DatabaseConfig,
    LLMConfig,
    LLMProfilesConfig,
    MemorizeConfig,
    RetrieveConfig,
    UserConfig,
)
from memu.blob.local_fs import LocalFS
from memu.database.factory import build_database
from memu.database.interfaces import Database
from memu.llm.http_client import HTTPLLMClient
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


class MemoryService(MemorizeMixin, RetrieveMixin, PatchMixin, CRUDMixin):
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
    ):
        self.llm_profiles = self._validate_config(llm_profiles, LLMProfilesConfig)
        self.user_config = self._validate_config(user_config, UserConfig)
        self.user_model = self.user_config.model
        self.llm_config = self._validate_config(self.llm_profiles.default, LLMConfig)
        self.blob_config = self._validate_config(blob_config, BlobConfig)
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.memorize_config = self._validate_config(memorize_config, MemorizeConfig)
        self.retrieve_config = self._validate_config(retrieve_config, RetrieveConfig)

        self.fs = LocalFS(self.blob_config.resources_dir)
        self.category_configs: list[dict[str, str]] = list(self.memorize_config.memory_categories or [])
        self._category_prompt_str = self._format_categories_for_prompt(self.category_configs)

        self._context = Context(categories_ready=not bool(self.category_configs))

        self.database: Database = build_database(
            config=self.database_config,
            user_model=self.user_model,
        )
        # We need the concrete user scope (user_id: xxx) to initialize the categories
        # self._start_category_initialization(self._context, self.database)

        # Initialize client caches (lazy creation on first use)
        self._llm_clients: dict[str, Any] = {}

        self._workflow_runner = resolve_workflow_runner(workflow_runner)

        self._pipelines = PipelineManager(
            available_capabilities={"llm", "vector", "db", "io", "vision"},
            llm_profiles=set(self.llm_profiles.profiles.keys()),
        )
        self._register_pipelines()

    def _init_llm_client(self, config: LLMConfig | None = None) -> Any:
        """Initialize LLM client based on configuration."""
        cfg = config or self.llm_config
        backend = cfg.client_backend
        if backend == "sdk":
            from memu.llm.openai_sdk import OpenAISDKClient

            return OpenAISDKClient(
                base_url=cfg.base_url,
                api_key=cfg.api_key,
                chat_model=cfg.chat_model,
                embed_model=cfg.embed_model,
                embed_batch_size=cfg.embed_batch_size,
            )
        elif backend == "httpx":
            return HTTPLLMClient(
                base_url=cfg.base_url,
                api_key=cfg.api_key,
                chat_model=cfg.chat_model,
                provider=cfg.provider,
                endpoint_overrides=cfg.endpoint_overrides,
                embed_model=cfg.embed_model,
            )
        else:
            msg = f"Unknown llm_client_backend '{cfg.client_backend}'"
            raise ValueError(msg)

    def _get_llm_client(self, profile: str | None = None) -> Any:
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

    @property
    def llm_client(self) -> Any:
        """Default LLM client (lazy)."""
        return self._get_llm_client()

    @property
    def workflow_runner(self) -> WorkflowRunner:
        """Current workflow runner backend."""
        return self._workflow_runner

    @staticmethod
    def _llm_profile_from_context(step_context: Mapping[str, Any] | None) -> str | None:
        if not isinstance(step_context, Mapping):
            return None
        step_cfg = step_context.get("step_config")
        if not isinstance(step_cfg, Mapping):
            return None
        profile = step_cfg.get("llm_profile")
        if isinstance(profile, str) and profile.strip():
            return profile.strip()
        return None

    def _get_step_llm_client(self, step_context: Mapping[str, Any] | None) -> Any:
        profile = self._llm_profile_from_context(step_context)
        return self._get_llm_client(profile)

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
        memorize_initial_keys = {
            "resource_url",
            "modality",
            "summary_prompt_override",
            "memory_types",
            "base_prompt",
            "categories_prompt_str",
            "ctx",
            "store",
            "category_ids",
            "user",
        }
        retrieve_initial_keys = {
            "original_query",
            "context_queries",
            "ctx",
            "store",
            "top_k",
            "skip_rewrite",
            "method",
            "where",
        }
        patch_create_initial_keys = {
            "memory_payload",
            "ctx",
            "store",
            "user",
        }
        patch_update_initial_keys = {
            "memory_id",
            "memory_payload",
            "ctx",
            "store",
            "user",
        }
        patch_delete_initial_keys = {
            "memory_id",
            "ctx",
            "store",
            "user",
        }
        crud_list_memories_initial_keys = {
            "ctx",
            "store",
            "where",
        }
        memo_workflow = self._build_memorize_workflow()
        self._pipelines.register("memorize", memo_workflow, initial_state_keys=memorize_initial_keys)
        rag_workflow = self._build_rag_retrieve_workflow()
        self._pipelines.register("retrieve_rag", rag_workflow, initial_state_keys=retrieve_initial_keys)
        llm_workflow = self._build_llm_retrieve_workflow()
        self._pipelines.register("retrieve_llm", llm_workflow, initial_state_keys=retrieve_initial_keys)
        patch_create_workflow = self._build_create_memory_item_workflow()
        self._pipelines.register("patch_create", patch_create_workflow, initial_state_keys=patch_create_initial_keys)
        patch_update_workflow = self._build_update_memory_item_workflow()
        self._pipelines.register("patch_update", patch_update_workflow, initial_state_keys=patch_update_initial_keys)
        patch_delete_workflow = self._build_delete_memory_item_workflow()
        self._pipelines.register("patch_delete", patch_delete_workflow, initial_state_keys=patch_delete_initial_keys)
        crud_list_items_workflow = self._build_list_memory_items_workflow()
        self._pipelines.register(
            "crud_list_memory_items", crud_list_items_workflow, initial_state_keys=crud_list_memories_initial_keys
        )
        crud_list_categories_workflow = self._build_list_memory_categories_workflow()
        self._pipelines.register(
            "crud_list_memory_categories",
            crud_list_categories_workflow,
            initial_state_keys=crud_list_memories_initial_keys,
        )

    async def _run_workflow(self, workflow_name: str, initial_state: WorkflowState) -> WorkflowState:
        """Execute a workflow through the configured runner backend."""
        steps = self._pipelines.build(workflow_name)
        runner_context = {"workflow_name": workflow_name}
        return await self._workflow_runner.run(workflow_name, steps, initial_state, runner_context)

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
