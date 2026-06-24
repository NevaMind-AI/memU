"""Memory file-system build orchestration, extracted from ``MemoryService``.

This collaborator owns the markdown "memory file system" artifact layer: the
exporter, the LLM synthesizer, and the write lock. ``MemoryService`` keeps a
thin ``_build_memory_files`` delegate so this stays an internal composition
detail, but the init-vs-incremental synthesis policy lives here rather than
bloating the service composition root.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from memu.memory_fs import ExistingArtifacts, ExportResult, MemoryFileExporter, MemorySynthesizer

if TYPE_CHECKING:
    from collections.abc import Callable

    from memu.app.settings import MemoryFilesConfig
    from memu.database.interfaces import Database


class MemoryFilesBuilder:
    """Initialize or incrementally update the markdown memory file tree.

    Holds the exporter/synthesizer/lock so the build policy is testable and
    decoupled from the rest of the service. Writes are serialized through a
    single lock so concurrent exports never interleave on the output directory.
    """

    def __init__(self, *, config: MemoryFilesConfig) -> None:
        self.config = config
        self.exporter = MemoryFileExporter(config.output_dir)
        self.synthesizer = MemorySynthesizer()
        self.lock = asyncio.Lock()

    async def build(
        self,
        database: Database,
        where: dict[str, Any] | None,
        *,
        changed: list[Any] | None,
        make_client: Callable[[str], Any],
    ) -> dict[str, Any]:
        """Initialize or incrementally update the memory file tree.

        ``changed`` is the list of just-memorized ``Resource`` objects driving an
        incremental update. When it is ``None`` (or no prior tree exists), the
        tree is (re)initialized from the full scoped store. ``make_client`` builds
        the LLM client used for synthesis from a profile name.

        LLM work only happens when ``synthesize=True``: MEMORY.md and the skill/
        tree are synthesized from the per-source descriptions. Otherwise both are
        left as ``None`` so the exporter renders MEMORY.md deterministically from
        category summaries and falls back to its rule-based skill bypass.
        """
        memory_body: str | None = None
        skills: dict[str, str] | None = None

        if self.config.synthesize:
            # The shared description trunk is the just-changed sources for an
            # incremental update, otherwise the full in-scope store.
            is_update = changed is not None and self.exporter.artifacts_exist()
            if is_update:
                descriptions = MemoryFileExporter._build_descriptions(changed)  # type: ignore[arg-type]
            else:
                resources = list(database.resource_repo.list_resources(where=where or None).values())
                descriptions = MemoryFileExporter._build_descriptions(resources)

            # An incremental update merges the changed descriptions into the prior
            # artifacts; a full (re)initialization starts from empty existing state
            # so stale entries are dropped (the exporter's manifest diff prunes any
            # files no longer produced).
            existing = await asyncio.to_thread(self.exporter.read_existing) if is_update else ExistingArtifacts()
            client = make_client(self.config.synthesis_llm_profile)
            synthesized = await self.synthesizer.synthesize(
                descriptions,
                existing_memory=existing.memory_body,
                existing_skills=existing.skills,
                chat=client.chat,
            )
            memory_body, skills = synthesized.memory_body, synthesized.skills

        async with self.lock:
            result: ExportResult = await asyncio.to_thread(
                self.exporter.export,
                database,
                where=where,
                memory_body=memory_body,
                skills=skills,
            )
        return result.to_dict()


__all__ = ["MemoryFilesBuilder"]
