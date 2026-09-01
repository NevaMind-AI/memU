from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from memu.database.inmemory.models import build_inmemory_models
from memu.database.inmemory.repositories import (
    InMemoryFileSegmentRepository,
    InMemoryRecallFileRepository,
    InMemoryResourceRepository,
)
from memu.database.inmemory.state import InMemoryState
from memu.database.interfaces import Database, EmbeddingSpaceMismatch
from memu.database.models import (
    RecallFile,
    RecallFileSegment,
    Resource,
)
from memu.database.repositories import RecallFileRepo, ResourceRepo

_REINDEX_CONFLICT = "record changed during embedding reindex"


class InMemoryStore(Database):
    def __init__(
        self,
        *,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        recall_file_model: type[Any] | None = None,
        recall_file_segment_model: type[Any] | None = None,
        state: InMemoryState | None = None,
    ) -> None:
        self.scope_model = scope_model or BaseModel
        (
            default_resource_model,
            default_recall_file_model,
            default_recall_file_segment_model,
        ) = build_inmemory_models(self.scope_model)

        self.state = state or InMemoryState()
        self.resources: dict[str, Resource] = self.state.resources
        self.recall_files: dict[str, RecallFile] = self.state.recall_files
        self.segments: list[RecallFileSegment] = self.state.segments

        resource_model = resource_model or default_resource_model or Resource
        recall_file_model = recall_file_model or default_recall_file_model or RecallFile
        recall_file_segment_model = recall_file_segment_model or default_recall_file_segment_model or RecallFileSegment

        self.resource_repo: ResourceRepo = InMemoryResourceRepository(state=self.state, resource_model=resource_model)
        self.recall_file_repo: RecallFileRepo = InMemoryRecallFileRepository(
            state=self.state, recall_file_model=recall_file_model
        )
        self.recall_file_segment_repo = InMemoryFileSegmentRepository(
            state=self.state, recall_file_segment_model=recall_file_segment_model
        )

    def close(self) -> None:
        return None

    def assert_embedding_space(self, embedding_space: str, *, initialize: bool = True) -> None:
        current = self.state.embedding_space
        if current == embedding_space:
            self.state.expected_embedding_space = embedding_space
            return
        has_vectors = (
            any(item.embedding for item in self.resources.values())
            or any(item.embedding for item in self.recall_files.values())
            or any(item.embedding for item in self.segments)
        )
        if has_vectors and current != embedding_space:
            raise EmbeddingSpaceMismatch
        self.state.expected_embedding_space = embedding_space
        if initialize:
            self.state.embedding_space = embedding_space

    def replace_all_embeddings(
        self,
        *,
        resources: Mapping[str, list[float]],
        recall_files: Mapping[str, list[float]],
        segments: Mapping[str, list[float]],
        embedding_space: str,
    ) -> None:
        segment_by_id = {item.id: item for item in self.segments}
        resource_ids = {item.id for item in self.resources.values() if item.caption}
        if set(resources) != resource_ids or set(recall_files) != self.recall_files.keys():
            raise KeyError(_REINDEX_CONFLICT)
        if set(segments) != segment_by_id.keys():
            raise KeyError(_REINDEX_CONFLICT)
        for item_id, vector in resources.items():
            self.resources[item_id].embedding = vector
        for item_id, vector in recall_files.items():
            self.recall_files[item_id].embedding = vector
        for item_id, vector in segments.items():
            segment_by_id[item_id].embedding = vector
        self.state.embedding_space = embedding_space
        self.state.expected_embedding_space = embedding_space
