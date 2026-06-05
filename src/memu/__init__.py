from __future__ import annotations

from typing import TYPE_CHECKING, Any

from memu._version import __version__

try:
    from memu._core import hello_from_bin
except ModuleNotFoundError as exc:
    if exc.name != "memu._core":
        raise

    # Source-tree imports during local tests may run before the Rust extension is built.
    def hello_from_bin() -> str:
        return "Hello from memu!"


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

    MemUService = MemoryService


_LAZY_EXPORTS = {
    "BlobConfig": ("memu.app.settings", "BlobConfig"),
    "DatabaseConfig": ("memu.app.settings", "DatabaseConfig"),
    "DefaultUserModel": ("memu.app.settings", "DefaultUserModel"),
    "LLMConfig": ("memu.app.settings", "LLMConfig"),
    "LLMProfilesConfig": ("memu.app.settings", "LLMProfilesConfig"),
    "LocalWorkflowRunner": ("memu.workflow.runner", "LocalWorkflowRunner"),
    "MemUService": ("memu.app.service", "MemoryService"),
    "MemorizeConfig": ("memu.app.settings", "MemorizeConfig"),
    "MemoryService": ("memu.app.service", "MemoryService"),
    "RetrieveConfig": ("memu.app.settings", "RetrieveConfig"),
    "UserConfig": ("memu.app.settings", "UserConfig"),
    "WorkflowRunner": ("memu.workflow.runner", "WorkflowRunner"),
    "register_workflow_runner": ("memu.workflow.runner", "register_workflow_runner"),
    "resolve_workflow_runner": ("memu.workflow.runner", "resolve_workflow_runner"),
}


def _rust_entry() -> str:
    return hello_from_bin()


__all__ = [
    "BlobConfig",
    "DEFAULT_CONTEXT_MAX_CHARS",
    "DEFAULT_MAX_TEXT_CHARS",
    "DatabaseConfig",
    "DefaultUserModel",
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
    "HARNESS_CONFIG_NAME",
    "HARNESS_CONFIG_VERSION",
    "ContextHarness",
    "ContextHarnessRun",
    "ContextHarnessSkillEvolutionResult",
    "ContextHarnessSkillTraceResult",
    "LLMConfig",
    "LLMProfilesConfig",
    "LocalWorkflowRunner",
    "MarkdownContextPack",
    "MarkdownContextSection",
    "MarkdownMemoryEntry",
    "MarkdownMemoryRepository",
    "EvidenceRecord",
    "EvolutionInstruction",
    "EvolutionReviewBundle",
    "EvolutionReviewConfig",
    "EvolutionReviewApplyResult",
    "MemUService",
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
    "__version__",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    if name == "MemoryService":
        globals().setdefault("MemUService", value)
    elif name == "MemUService":
        globals().setdefault("MemoryService", value)
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY_EXPORTS))
