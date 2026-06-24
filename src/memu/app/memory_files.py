"""Memory file-system build orchestration, extracted from ``MemoryService``.

This collaborator owns the markdown "memory file system" artifact layer: the
exporter, the LLM synthesizer, and the write lock. ``MemoryService`` keeps a
thin ``_build_memory_files`` delegate so this stays an internal composition
detail, but the ~70 lines of init-vs-incremental synthesis policy live here
rather than bloating the service composition root.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from memu.memory_fs import ExportResult, MemoryFileExporter, MemorySynthesizer

if TYPE_CHECKING:
    from memu.app.settings import MemoryFilesConfig
    from memu.database.interfaces import Database

# A factory that returns a wrapped LLM client (exposing ``.chat``) for a profile.
MakeClient = Callable[[str], Any]


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
        make_client: MakeClient,
    ) -> dict[str, Any]:
        """Initialize or incrementally update the memory file tree.

        ``changed`` is the list of just-memorized ``Resource`` objects driving an
        incremental update. When it is ``None`` (or no prior tree exists), the
        tree is (re)initialized from the full scoped store. ``make_client`` builds
        the LLM client used for synthesis from a profile name.
        """
        memory_body: str | None = None
        skills: dict[str, str] | None = None

        is_update = changed is not None and self.exporter.artifacts_exist()

        # The synthesis trunk is the structured store (extracted memory items), not the
        # lossy per-source captions: the just-changed sources for an incremental update,
        # otherwise the full in-scope store for (re)initialization.
        scoped_items = list(database.memory_item_repo.list_items(where=where or None).values())
        if is_update:
            changed_resources = list(changed or [])
            changed_ids = {res.id for res in changed_resources}
            changed_items = [item for item in scoped_items if item.resource_id in changed_ids]
            descriptions = MemoryFileExporter.build_synthesis_descriptions(changed_resources, changed_items)
        else:
            resources = list(database.resource_repo.list_resources(where=where or None).values())
            descriptions = MemoryFileExporter.build_synthesis_descriptions(resources, scoped_items)

        client = make_client(self.config.synthesis_llm_profile)
        chat: Callable[..., Awaitable[Any]] = client.chat

        if self.config.synthesize:
            # MEMORY.md and the skill/ tree are both synthesized from descriptions.
            if is_update:
                existing_memory = await asyncio.to_thread(self.exporter.read_memory_body)
                existing_skills = await asyncio.to_thread(self.exporter.read_skills)
                synthesized = await self.synthesizer.update(
                    descriptions,
                    existing_memory=existing_memory,
                    existing_skills=existing_skills,
                    chat=chat,
                )
            else:
                synthesized = await self.synthesizer.synthesize(descriptions, chat=chat)
            memory_body, skills = synthesized.memory_body, synthesized.skills
        else:
            # MEMORY.md is rendered deterministically from category summaries, but
            # the skill/ tree is a sibling bypass: always synthesized from the
            # descriptions, never derived from extracted skill-type memory items.
            if is_update:
                existing_skills = await asyncio.to_thread(self.exporter.read_skills)
                skills = await self.synthesizer.update_skills(descriptions, existing_skills=existing_skills, chat=chat)
            else:
                skills = await self.synthesizer.synthesize_skills(descriptions, chat=chat)

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
