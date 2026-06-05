from __future__ import annotations

from typing import TYPE_CHECKING, Any

from memu.app.context_harness import (
    ContextHarness,
    ContextHarnessRun,
    ContextHarnessSkillEvolutionResult,
    ContextHarnessSkillTraceResult,
)
from memu.app.folder import (
    EvolutionReviewApplyResult,
    FolderCompileResult,
    FolderHealthIssue,
    FolderHealthResult,
    FolderHealthSeverity,
    FolderMemoryCompiler,
    FolderMemoryCompilerConfig,
    FolderScaffoldResult,
    FolderSourceState,
    FolderSourceStatus,
    FolderStatusResult,
    FolderWatchEvent,
    MarkdownMemoryEntry,
    compile_folder_to_markdown,
    compile_folder_to_markdown_sync,
    inspect_folder_memory_health,
    inspect_folder_memory_status,
    review_folder_evolution,
    scaffold_folder_memory_repository,
    watch_folder_to_markdown,
    watch_folder_to_markdown_sync,
)
from memu.app.harness_config import (
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_MAX_TEXT_CHARS,
    HARNESS_CONFIG_NAME,
    HARNESS_CONFIG_VERSION,
    default_harness_config,
    harness_config_path,
    load_harness_config,
    validate_harness_config,
)
from memu.app.markdown_context import (
    MarkdownContextPack,
    MarkdownContextSection,
    MarkdownMemoryRepository,
    build_markdown_context_pack,
    inject_context_messages,
)
from memu.app.self_evolve import (
    EvidenceRecord,
    EvolutionInstruction,
    EvolutionReviewBundle,
    EvolutionReviewConfig,
    PatchProposal,
    ReviewDecision,
    ReviewStatus,
)
from memu.app.skill_trace import (
    SkillEvolutionProposal,
    SkillPromotionRecord,
    SkillToolTrace,
    SkillTrace,
    SkillTraceRecord,
    promote_skill,
    record_skill_trace,
    suggest_skill_promotions,
)

if TYPE_CHECKING:
    from memu.app.service import MemoryService
    from memu.app.settings import (
        BlobConfig,
        DatabaseConfig,
        DefaultUserModel,
        LLMConfig,
        LLMProfilesConfig,
        MemorizeConfig,
        RetrieveConfig,
        UserConfig,
    )
    from memu.workflow.runner import (
        LocalWorkflowRunner,
        WorkflowRunner,
        register_workflow_runner,
        resolve_workflow_runner,
    )


_LAZY_EXPORTS = {
    "BlobConfig": ("memu.app.settings", "BlobConfig"),
    "DatabaseConfig": ("memu.app.settings", "DatabaseConfig"),
    "DefaultUserModel": ("memu.app.settings", "DefaultUserModel"),
    "LLMConfig": ("memu.app.settings", "LLMConfig"),
    "LLMProfilesConfig": ("memu.app.settings", "LLMProfilesConfig"),
    "LocalWorkflowRunner": ("memu.workflow.runner", "LocalWorkflowRunner"),
    "MemorizeConfig": ("memu.app.settings", "MemorizeConfig"),
    "MemoryService": ("memu.app.service", "MemoryService"),
    "RetrieveConfig": ("memu.app.settings", "RetrieveConfig"),
    "UserConfig": ("memu.app.settings", "UserConfig"),
    "WorkflowRunner": ("memu.workflow.runner", "WorkflowRunner"),
    "register_workflow_runner": ("memu.workflow.runner", "register_workflow_runner"),
    "resolve_workflow_runner": ("memu.workflow.runner", "resolve_workflow_runner"),
}

__all__ = [
    "BlobConfig",
    "ContextHarness",
    "ContextHarnessRun",
    "ContextHarnessSkillEvolutionResult",
    "ContextHarnessSkillTraceResult",
    "DatabaseConfig",
    "DefaultUserModel",
    "EvidenceRecord",
    "EvolutionInstruction",
    "EvolutionReviewBundle",
    "EvolutionReviewConfig",
    "EvolutionReviewApplyResult",
    "FolderCompileResult",
    "FolderHealthIssue",
    "FolderHealthResult",
    "FolderHealthSeverity",
    "FolderMemoryCompiler",
    "FolderMemoryCompilerConfig",
    "FolderScaffoldResult",
    "FolderSourceState",
    "FolderSourceStatus",
    "FolderStatusResult",
    "FolderWatchEvent",
    "DEFAULT_CONTEXT_MAX_CHARS",
    "DEFAULT_MAX_TEXT_CHARS",
    "HARNESS_CONFIG_NAME",
    "HARNESS_CONFIG_VERSION",
    "LLMConfig",
    "LLMProfilesConfig",
    "LocalWorkflowRunner",
    "MarkdownContextPack",
    "MarkdownContextSection",
    "MarkdownMemoryEntry",
    "MarkdownMemoryRepository",
    "MemorizeConfig",
    "MemoryService",
    "PatchProposal",
    "ReviewDecision",
    "ReviewStatus",
    "RetrieveConfig",
    "SkillEvolutionProposal",
    "SkillPromotionRecord",
    "SkillToolTrace",
    "SkillTrace",
    "SkillTraceRecord",
    "UserConfig",
    "WorkflowRunner",
    "build_markdown_context_pack",
    "compile_folder_to_markdown",
    "compile_folder_to_markdown_sync",
    "default_harness_config",
    "harness_config_path",
    "inspect_folder_memory_health",
    "inject_context_messages",
    "inspect_folder_memory_status",
    "load_harness_config",
    "review_folder_evolution",
    "register_workflow_runner",
    "resolve_workflow_runner",
    "promote_skill",
    "record_skill_trace",
    "scaffold_folder_memory_repository",
    "suggest_skill_promotions",
    "validate_harness_config",
    "watch_folder_to_markdown",
    "watch_folder_to_markdown_sync",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY_EXPORTS))
