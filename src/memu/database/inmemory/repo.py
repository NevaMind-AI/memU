from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from memu.database.inmemory.models import build_inmemory_models
from memu.database.inmemory.repositories import (
    InMemoryFileResourceRepository,
    InMemoryFileSegmentRepository,
    InMemoryRecallFileRepository,
    InMemoryResourceRepository,
)
from memu.database.inmemory.state import InMemoryState
from memu.database.interfaces import Database
from memu.database.models import (
    RecallFile,
    RecallFileResource,
    RecallFileSegment,
    Resource,
)
from memu.database.repositories import RecallFileRepo, ResourceRepo


class InMemoryStore(Database):
    def __init__(
        self,
        *,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        recall_file_model: type[Any] | None = None,
        recall_file_resource_model: type[Any] | None = None,
        recall_file_segment_model: type[Any] | None = None,
        state: InMemoryState | None = None,
    ) -> None:
        self.scope_model = scope_model or BaseModel
        (
            default_resource_model,
            default_recall_file_model,
            default_recall_file_resource_model,
            default_recall_file_segment_model,
        ) = build_inmemory_models(self.scope_model)

        self.state = state or InMemoryState()
        self.resources: dict[str, Resource] = self.state.resources
        self.categories: dict[str, RecallFile] = self.state.categories
        self.resource_relations: list[RecallFileResource] = self.state.resource_relations
        self.segments: list[RecallFileSegment] = self.state.segments

        resource_model = resource_model or default_resource_model or Resource
        recall_file_model = recall_file_model or default_recall_file_model or RecallFile
        recall_file_resource_model = (
            recall_file_resource_model or default_recall_file_resource_model or RecallFileResource
        )
        recall_file_segment_model = recall_file_segment_model or default_recall_file_segment_model or RecallFileSegment

        self.resource_repo: ResourceRepo = InMemoryResourceRepository(state=self.state, resource_model=resource_model)
        self.recall_file_repo: RecallFileRepo = InMemoryRecallFileRepository(
            state=self.state, recall_file_model=recall_file_model
        )
        self.recall_file_resource_repo = InMemoryFileResourceRepository(
            state=self.state, recall_file_resource_model=recall_file_resource_model
        )
        self.recall_file_segment_repo = InMemoryFileSegmentRepository(
            state=self.state, recall_file_segment_model=recall_file_segment_model
        )

    def close(self) -> None:
        return None
