from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from memu.app.memorize import MemorizeMixin
from memu.app.retrieve import RetrieveMixin
from memu.app.settings import (
    BlobConfig,
    DatabaseConfig,
    LLMConfig,
    LLMProfilesConfig,
    MemorizeConfig,
    RetrieveConfig,
    StorageProvidersConfig,
    UserConfig,
)
from memu.blob.local_fs import LocalFS
from memu.database.factory import init_database_layer
from memu.llm.http_client import HTTPLLMClient
from memu.workflow.pipeline import PipelineManager
from memu.workflow.runner import WorkflowRunner, resolve_workflow_runner
from memu.workflow.step import WorkflowState, WorkflowStep

TConfigModel = TypeVar("TConfigModel", bound=BaseModel)


class MemoryService(MemorizeMixin, RetrieveMixin):
    def __init__(
        self,
        *,
        llm_profiles: LLMProfilesConfig | dict[str, Any] | None = None,
        blob_config: BlobConfig | dict[str, Any] | None = None,
        database_config: DatabaseConfig | dict[str, Any] | None = None,
        storage_providers: StorageProvidersConfig | dict[str, Any] | None = None,
        memorize_config: MemorizeConfig | dict[str, Any] | None = None,
        retrieve_config: RetrieveConfig | dict[str, Any] | None = None,
        workflow_runner: WorkflowRunner | str | None = None,
        user_config: UserConfig | dict[str, Any] | None = None,
    ):
        self.llm_profiles = self._validate_config(llm_profiles, LLMProfilesConfig)
        self.user_config = self._validate_config(user_config, UserConfig)
        self.user_model = self.user_config.model
        self.llm_config = self.llm_profiles.default
        self.blob_config = self._validate_config(blob_config, BlobConfig)
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.storage_providers = self._validate_config(storage_providers, StorageProvidersConfig)
        self.memorize_config = self._validate_config(memorize_config, MemorizeConfig)
        self.retrieve_config = self._validate_config(retrieve_config, RetrieveConfig)
        db_layer = init_database_layer(
            user_model=self.user_model,
            database_config=self.database_config,
            storage_providers=self.storage_providers,
        )
        self.base_model_cls = db_layer.base_model
        self.resource_model = db_layer.resource_model
        self.memory_item_model = db_layer.memory_item_model
        self.memory_category_model = db_layer.memory_category_model
        self.category_item_model = db_layer.category_item_model
        self._store_factory = db_layer.store_factory
        self.fs = LocalFS(self.blob_config.resources_dir)

        # Initialize client caches (lazy creation on first use)
        self._llm_clients: dict[str, Any] = {}

        self.category_configs: list[dict[str, str]] = list(self.memorize_config.memory_categories or [])
        self._category_prompt_str = self._format_categories_for_prompt(self.category_configs)

        self._start_category_initialization(default_context)

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
        name = profile or self.llm_profiles.default
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

    def _provider_summary(self) -> dict[str, Any]:
        vector_provider = None
        if self.storage_providers.vector_index:
            vector_provider = self.storage_providers.vector_index.provider
        return {
            "llm_profiles": list(self.llm_profiles.profiles.keys()),
            "storage": {
                "metadata_store": self.storage_providers.metadata_store.provider,
                "vector_index": vector_provider,
            },
        }

    def _pipeline_revision_token(self) -> str:
        return self._pipelines.revision_token()

    def _register_pipelines(self) -> None:
        memorize_initial_keys = {
            "resource_url",
            "modality",
            "summary_prompt_override",
            "memory_types",
            "base_prompt",
            "categories_prompt_str",
            "ctx",
            "category_ids",
        }
        retrieve_initial_keys = {"original_query", "context_queries", "ctx", "top_k", "skip_rewrite", "method"}
        memo_workflow = self._build_memorize_workflow()
        self._pipelines.register("memorize", memo_workflow.steps, initial_state_keys=memorize_initial_keys)
        rag_workflow = self._build_rag_retrieve_workflow()
        self._pipelines.register("retrieve_rag", rag_workflow.steps, initial_state_keys=retrieve_initial_keys)
        llm_workflow = self._build_llm_retrieve_workflow()
        self._pipelines.register("retrieve_llm", llm_workflow.steps, initial_state_keys=retrieve_initial_keys)

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

    def _refresh_pipeline_revision(self) -> None:
        self.service_meta = self.service_meta.with_pipeline_revision(self._pipeline_revision_token())

    def configure_pipeline(self, *, step_id: str, configs: Mapping[str, Any], pipeline: str = "memorize") -> int:
        revision = self._pipelines.config_step(pipeline, step_id, dict(configs))
        self._refresh_pipeline_revision()
        return revision

    def insert_step_after(
        self,
        *,
        target_step_id: str,
        new_step: WorkflowStep,
        pipeline: str = "memorize",
    ) -> int:
        revision = self._pipelines.insert_after(pipeline, target_step_id, new_step)
        self._refresh_pipeline_revision()
        return revision

    def insert_step_before(
        self,
        *,
        target_step_id: str,
        new_step: WorkflowStep,
        pipeline: str = "memorize",
    ) -> int:
        revision = self._pipelines.insert_before(pipeline, target_step_id, new_step)
        self._refresh_pipeline_revision()
        return revision

    def replace_step(
        self,
        *,
        target_step_id: str,
        new_step: WorkflowStep,
        pipeline: str = "memorize",
    ) -> int:
        revision = self._pipelines.replace_step(pipeline, target_step_id, new_step)
        self._refresh_pipeline_revision()
        return revision

    def remove_step(self, *, target_step_id: str, pipeline: str = "memorize") -> int:
        revision = self._pipelines.remove_step(pipeline, target_step_id)
        self._refresh_pipeline_revision()
        return revision
