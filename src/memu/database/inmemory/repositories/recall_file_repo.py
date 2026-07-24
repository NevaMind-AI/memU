from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import pendulum

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import RecallFile
from memu.database.repositories.recall_file import RecallFileRepo as RecallFileRepoProtocol


class InMemoryRecallFileRepository(RecallFileRepoProtocol):
    def __init__(self, *, state: InMemoryState, recall_file_model: type[RecallFile]) -> None:
        self._state = state
        self.recall_file_model = recall_file_model
        self.recall_files: dict[str, RecallFile] = self._state.recall_files

    def list_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        if not where:
            return dict(self.recall_files)
        return {rid: recall_file for rid, recall_file in self.recall_files.items() if matches_where(recall_file, where)}

    def clear_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        if not where:
            matches = self.recall_files.copy()
            self.recall_files.clear()
            return matches
        matches = {
            rid: recall_file for rid, recall_file in self.recall_files.items() if matches_where(recall_file, where)
        }
        for rid in matches:
            self.recall_files.pop(rid, None)
        return matches

    def get_or_create_recall_file(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFile:
        for recall_file in self.recall_files.values():
            if (
                recall_file.name == name
                and recall_file.track == track
                and all(getattr(recall_file, k) == v for k, v in user_data.items())
            ):
                now = pendulum.now("UTC")
                if recall_file.embedding is None:
                    recall_file.embedding = embedding
                    recall_file.updated_at = now
                if not recall_file.description:
                    recall_file.description = description
                    recall_file.updated_at = now
                return recall_file
        rid = str(uuid.uuid4())
        recall_file = self.recall_file_model(
            id=rid, name=name, description=description, embedding=embedding, track=track, **user_data
        )
        self.recall_files[rid] = recall_file
        return recall_file

    def update_recall_file(
        self,
        *,
        recall_file_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        content: str | None = None,
    ) -> RecallFile:
        recall_file = self.recall_files.get(recall_file_id)
        if recall_file is None:
            msg = f"RecallFile with id {recall_file_id} not found"
            raise KeyError(msg)

        if name is not None:
            recall_file.name = name
        if description is not None:
            recall_file.description = description
        if embedding is not None:
            recall_file.embedding = embedding
        if content is not None:
            recall_file.content = content

        recall_file.updated_at = pendulum.now("UTC")
        return recall_file

    def load_existing(self) -> None:
        return None


RecallFileRepo = InMemoryRecallFileRepository

__all__ = ["InMemoryRecallFileRepository", "RecallFileRepo"]
