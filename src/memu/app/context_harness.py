from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from memu.app.folder import (
    EvolutionReviewApplyResult,
    FolderCompileResult,
    FolderHealthIssue,
    FolderMemoryCompiler,
    FolderMemoryCompilerConfig,
    FolderHealthResult,
    FolderScaffoldResult,
    FolderStatusResult,
    FolderWatchEvent,
    watch_folder_to_markdown,
    watch_folder_to_markdown_sync,
)
from memu.app.harness_config import (
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_MAX_TEXT_CHARS,
    HARNESS_CONFIG_NAME,
    arg_or_config_positive_int,
    compiler_exclude_patterns,
    config_bucket_char_limits,
    config_context_buckets,
    config_section,
    harness_config_path,
    try_load_harness_config,
    validate_harness_config,
)
from memu.app.markdown_context import ContextBucket, MarkdownContextPack, MarkdownMemoryRepository
from memu.app.self_evolve import ReviewStatus
from memu.app.skill_trace import (
    SkillEvolutionProposal,
    SkillPromotionRecord,
    SkillToolTrace,
    SkillTraceOutcome,
    SkillTraceRecord,
    promote_skill,
    record_skill_trace,
    suggest_skill_promotions,
)

if TYPE_CHECKING:
    from memu.app.service import MemoryService


@dataclass(frozen=True)
class ContextHarnessRun:
    """Result of compiling raw data and building a context pack in one call."""

    compile_result: FolderCompileResult
    context_pack: MarkdownContextPack


@dataclass(frozen=True)
class ContextHarnessSkillTraceResult:
    """Result of recording a skill trace, optionally followed by recompilation."""

    record: SkillTraceRecord
    compile_result: FolderCompileResult | None = None


@dataclass(frozen=True)
class ContextHarnessSkillEvolutionResult:
    """Result of suggesting skill promotions and optionally applying them."""

    proposals: list[SkillEvolutionProposal]
    promotions: list[SkillPromotionRecord]


class ContextHarness:
    """High-level harness for folder-backed memory, context, and skill evolution.

    `source_folder` is the user's raw-data folder. `repo_dir` is the Markdown memory
    repository containing `memory.md`, `soul.md`, `skill.md`, and `.memu/`.
    """

    def __init__(
        self,
        source_folder: str | Path,
        repo_dir: str | Path,
        *,
        memory_service: MemoryService | None = None,
        user: Mapping[str, Any] | None = None,
        compiler_config: FolderMemoryCompilerConfig | None = None,
        harness_config: Mapping[str, Any] | None = None,
    ) -> None:
        self.source_folder = Path(source_folder).resolve()
        self.repo_dir = Path(repo_dir).resolve()
        self.memory_service = memory_service
        self.user = dict(user or {})
        base_compiler_config = compiler_config or FolderMemoryCompilerConfig()
        self.harness_config_path = harness_config_path(
            self.repo_dir,
            base_compiler_config.metadata_dir_name,
        )
        self._harness_config_error: str | None = None
        self.harness_config = self._load_repo_harness_config(
            harness_config,
            metadata_dir_name=base_compiler_config.metadata_dir_name,
        )
        self.compiler_config = self._compiler_config_from_repo_config(base_compiler_config)
        self.compiler = FolderMemoryCompiler(memory_service=memory_service, config=self.compiler_config)
        self.repository = MarkdownMemoryRepository(self.repo_dir)

    @classmethod
    def from_repo(
        cls,
        repo_dir: str | Path,
        *,
        memory_service: MemoryService | None = None,
        user: Mapping[str, Any] | None = None,
        compiler_config: FolderMemoryCompilerConfig | None = None,
        harness_config: Mapping[str, Any] | None = None,
    ) -> ContextHarness:
        """Create a harness for an existing repository, using `repo/raw_data` as source."""

        base_compiler_config = compiler_config or FolderMemoryCompilerConfig()
        repo_path = Path(repo_dir)
        return cls(
            repo_path / base_compiler_config.raw_data_dir_name,
            repo_path,
            memory_service=memory_service,
            user=user,
            compiler_config=compiler_config,
            harness_config=harness_config,
        )

    def scaffold(self, *, copy_source: bool = False) -> FolderScaffoldResult:
        """Create the repository layout, optionally copying `source_folder` into raw_data."""

        self._ensure_harness_config_valid()
        source_folder = self.source_folder if copy_source else None
        return self.compiler.scaffold(self.repo_dir, source_folder=source_folder)

    def status(self) -> FolderStatusResult:
        """Inspect source changes against the manifest without writing files."""

        self._ensure_harness_config_valid()
        return self.compiler.status(self.source_folder, self.repo_dir)

    def health(self) -> FolderHealthResult:
        """Validate the Markdown memory repository without writing files."""

        result = self.compiler.health(self.repo_dir)
        issues = list(result.issues)
        if self._harness_config_error is not None:
            issues.append(
                FolderHealthIssue(
                    severity="error",
                    code="invalid_harness_config",
                    message=self._harness_config_error,
                    path=f"{self.compiler_config.metadata_dir_name}/{HARNESS_CONFIG_NAME}",
                )
            )
        return FolderHealthResult(output_dir=result.output_dir, issues=issues)

    def promote_skill(
        self,
        *,
        title: str,
        lessons: Sequence[str] | None = None,
        actions: Sequence[str] | None = None,
        when_to_use: str = "",
        source: str = "",
        tags: Sequence[str] | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> SkillPromotionRecord:
        """Append a durable manual skill note outside the generated block."""

        self._ensure_harness_config_valid()
        return promote_skill(
            self.repo_dir,
            title=title,
            lessons=list(lessons or []),
            actions=list(actions or []),
            when_to_use=when_to_use,
            source=source,
            tags=list(tags or []),
            metadata=dict(metadata or {}),
        )

    def review_evolution(
        self,
        *,
        proposal_ids: Sequence[str] | None = None,
        reviewer: str = "creator",
        decision: ReviewStatus = "approved",
        reason: str = "",
    ) -> EvolutionReviewApplyResult:
        """Apply creator review decisions to pending self-evolve proposals."""

        self._ensure_harness_config_valid()
        return self.compiler.review_evolution(
            self.repo_dir,
            proposal_ids=proposal_ids,
            reviewer=reviewer,
            decision=decision,
            reason=reason,
        )

    def suggest_skills(
        self,
        *,
        limit: int = 5,
        min_support: int = 1,
    ) -> list[SkillEvolutionProposal]:
        """Suggest durable skill promotions from recorded raw skill traces."""

        self._ensure_harness_config_valid()
        return suggest_skill_promotions(self.source_folder, limit=limit, min_support=min_support)

    def evolve_skills(
        self,
        *,
        limit: int = 5,
        min_support: int = 1,
        promote: bool = False,
    ) -> ContextHarnessSkillEvolutionResult:
        """Suggest skill promotions and optionally write them into the skill library."""

        proposals = self.suggest_skills(limit=limit, min_support=min_support)
        promotions = [self.promote_skill(**proposal.to_promotion_kwargs()) for proposal in proposals] if promote else []
        return ContextHarnessSkillEvolutionResult(proposals=proposals, promotions=promotions)

    async def ingest(self, *, user: Mapping[str, Any] | None = None) -> FolderCompileResult:
        """Compile changed raw data through self-evolve review into the Markdown repository."""

        self._ensure_harness_config_valid()
        return await self.compiler.compile(self.source_folder, self.repo_dir, user=self._scope(user))

    def ingest_sync(self, *, user: Mapping[str, Any] | None = None) -> FolderCompileResult:
        """Synchronous wrapper around `ingest`."""

        return asyncio.run(self.ingest(user=user))

    def build_context_pack(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
    ) -> MarkdownContextPack:
        """Load the Markdown repository into an agent-ready context pack."""

        self._ensure_harness_config_valid()
        return self.repository.build_context_pack(
            query=query,
            buckets=self._context_buckets(buckets),
            max_chars=self._context_max_chars(max_chars),
            include_generated=include_generated,
            include_manual=include_manual,
            bucket_char_limits=self._context_bucket_char_limits(bucket_char_limits),
        )

    def build_context_markdown(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
    ) -> str:
        """Return the context pack as `<memu_context>` Markdown."""

        return self.build_context_pack(
            query=query,
            buckets=buckets,
            max_chars=max_chars,
            include_generated=include_generated,
            include_manual=include_manual,
            bucket_char_limits=bucket_char_limits,
        ).to_markdown()

    def build_context_system_prompt(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
    ) -> str:
        """Return context with explicit system instructions for agent injection."""

        return self.build_context_pack(
            query=query,
            buckets=buckets,
            max_chars=max_chars,
            include_generated=include_generated,
            include_manual=include_manual,
            bucket_char_limits=bucket_char_limits,
        ).to_system_prompt()

    def build_context_messages(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
    ) -> list[dict[str, str]]:
        """Return context as a system message list for chat-completion APIs."""

        return self.build_context_pack(
            query=query,
            buckets=buckets,
            max_chars=max_chars,
            include_generated=include_generated,
            include_manual=include_manual,
            bucket_char_limits=bucket_char_limits,
        ).to_messages()

    def inject_context_messages(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
        replace_existing: bool = True,
    ) -> list[dict[str, Any]]:
        """Return a copied chat message list with memU context injected."""

        return self.build_context_pack(
            query=query,
            buckets=buckets,
            max_chars=max_chars,
            include_generated=include_generated,
            include_manual=include_manual,
            bucket_char_limits=bucket_char_limits,
        ).inject_into_messages(messages, replace_existing=replace_existing)

    async def refresh_context(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> ContextHarnessRun:
        """Compile raw data, then build a fresh context pack."""

        compile_result = await self.ingest(user=user)
        context_pack = self.build_context_pack(
            query=query,
            buckets=buckets,
            max_chars=max_chars,
            include_generated=include_generated,
            include_manual=include_manual,
            bucket_char_limits=bucket_char_limits,
        )
        return ContextHarnessRun(compile_result=compile_result, context_pack=context_pack)

    def refresh_context_sync(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> ContextHarnessRun:
        """Synchronous wrapper around `refresh_context`."""

        return asyncio.run(
            self.refresh_context(
                query=query,
                buckets=buckets,
                max_chars=max_chars,
                include_generated=include_generated,
                include_manual=include_manual,
                bucket_char_limits=bucket_char_limits,
                user=user,
            )
        )

    async def record_skill_trace(
        self,
        *,
        task: str,
        outcome: SkillTraceOutcome = "unknown",
        summary: str = "",
        actions: Sequence[str] | None = None,
        tools: Sequence[SkillToolTrace] | None = None,
        lessons: Sequence[str] | None = None,
        metadata: Mapping[str, str] | None = None,
        recompile: bool = True,
        user: Mapping[str, Any] | None = None,
    ) -> ContextHarnessSkillTraceResult:
        """Record skill-evolution evidence under raw data and optionally recompile."""

        record = record_skill_trace(
            self.source_folder,
            task=task,
            outcome=outcome,
            summary=summary,
            actions=list(actions or []),
            tools=list(tools or []),
            lessons=list(lessons or []),
            metadata=dict(metadata or {}),
        )
        compile_result = await self.ingest(user=user) if recompile else None
        return ContextHarnessSkillTraceResult(record=record, compile_result=compile_result)

    def record_skill_trace_sync(
        self,
        *,
        task: str,
        outcome: SkillTraceOutcome = "unknown",
        summary: str = "",
        actions: Sequence[str] | None = None,
        tools: Sequence[SkillToolTrace] | None = None,
        lessons: Sequence[str] | None = None,
        metadata: Mapping[str, str] | None = None,
        recompile: bool = True,
        user: Mapping[str, Any] | None = None,
    ) -> ContextHarnessSkillTraceResult:
        """Synchronous wrapper around `record_skill_trace`."""

        return asyncio.run(
            self.record_skill_trace(
                task=task,
                outcome=outcome,
                summary=summary,
                actions=actions,
                tools=tools,
                lessons=lessons,
                metadata=metadata,
                recompile=recompile,
                user=user,
            )
        )

    async def watch(
        self,
        *,
        poll_interval: float = 2.0,
        max_runs: int | None = None,
        on_event: Callable[[FolderWatchEvent], Any | Awaitable[Any]] | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> list[FolderWatchEvent]:
        """Watch raw data and recompile whenever the source fingerprint changes."""

        self._ensure_harness_config_valid()
        return await watch_folder_to_markdown(
            self.source_folder,
            self.repo_dir,
            memory_service=self.memory_service,
            user=self._scope(user),
            config=self.compiler_config,
            poll_interval=poll_interval,
            max_runs=max_runs,
            on_event=on_event,
        )

    def watch_sync(
        self,
        *,
        poll_interval: float = 2.0,
        max_runs: int | None = None,
        on_event: Callable[[FolderWatchEvent], Any | Awaitable[Any]] | None = None,
        user: Mapping[str, Any] | None = None,
    ) -> list[FolderWatchEvent]:
        """Synchronous wrapper around `watch`."""

        self._ensure_harness_config_valid()
        return watch_folder_to_markdown_sync(
            self.source_folder,
            self.repo_dir,
            memory_service=self.memory_service,
            user=self._scope(user),
            config=self.compiler_config,
            poll_interval=poll_interval,
            max_runs=max_runs,
            on_event=on_event,
        )

    def _scope(self, user: Mapping[str, Any] | None) -> dict[str, Any]:
        scope = dict(self.user)
        if user is not None:
            scope.update(user)
        return scope

    def _load_repo_harness_config(
        self,
        harness_config: Mapping[str, Any] | None,
        *,
        metadata_dir_name: str,
    ) -> dict[str, Any]:
        if harness_config is not None:
            try:
                validate_harness_config(harness_config, self.harness_config_path)
            except SystemExit as exc:
                self._harness_config_error = str(exc)
                return {}
            return dict(harness_config)
        config, error = try_load_harness_config(self.repo_dir, metadata_dir_name)
        self._harness_config_error = error
        return config

    def _ensure_harness_config_valid(self) -> None:
        if self._harness_config_error is not None:
            raise SystemExit(self._harness_config_error)

    def _compiler_config_from_repo_config(
        self,
        base_config: FolderMemoryCompilerConfig,
    ) -> FolderMemoryCompilerConfig:
        compiler_section = config_section(
            self.harness_config,
            "compiler",
            self.harness_config_path,
        )
        return FolderMemoryCompilerConfig(
            raw_data_dir_name=base_config.raw_data_dir_name,
            metadata_dir_name=base_config.metadata_dir_name,
            derived_dir_name=base_config.derived_dir_name,
            agent_instructions_name=base_config.agent_instructions_name,
            ignore_file_name=base_config.ignore_file_name,
            write_agent_instructions=base_config.write_agent_instructions,
            exclude_patterns=tuple(
                compiler_exclude_patterns(
                    list(base_config.exclude_patterns) if base_config.exclude_patterns else None,
                    compiler_section,
                    self.harness_config_path,
                )
            ),
            max_text_chars=arg_or_config_positive_int(
                base_config.max_text_chars if base_config.max_text_chars != DEFAULT_MAX_TEXT_CHARS else None,
                compiler_section,
                "max_text_chars",
                DEFAULT_MAX_TEXT_CHARS,
                flag_name="--max-text-chars",
                config_path=self.harness_config_path,
            ),
            use_memory_service=base_config.use_memory_service,
            self_evolve_enabled=base_config.self_evolve_enabled,
            evolution_review=base_config.evolution_review,
        )

    def _context_section(self) -> Mapping[str, Any]:
        return config_section(self.harness_config, "context", self.harness_config_path)

    def _context_buckets(
        self,
        buckets: Sequence[ContextBucket] | None,
    ) -> Sequence[ContextBucket] | None:
        if buckets is not None:
            return buckets
        configured = config_context_buckets(self._context_section(), self.harness_config_path)
        return [cast(ContextBucket, bucket) for bucket in configured] or None

    def _context_max_chars(self, max_chars: int | None) -> int:
        return arg_or_config_positive_int(
            max_chars,
            self._context_section(),
            "max_chars",
            DEFAULT_CONTEXT_MAX_CHARS,
            flag_name="max_chars",
            config_path=self.harness_config_path,
        )

    def _context_bucket_char_limits(
        self,
        bucket_char_limits: Mapping[ContextBucket, int] | None,
    ) -> Mapping[ContextBucket, int] | None:
        if bucket_char_limits is not None:
            return bucket_char_limits
        return config_bucket_char_limits(self._context_section(), self.harness_config_path)


__all__ = [
    "ContextHarness",
    "ContextHarnessRun",
    "ContextHarnessSkillEvolutionResult",
    "ContextHarnessSkillTraceResult",
    "EvolutionReviewApplyResult",
]
