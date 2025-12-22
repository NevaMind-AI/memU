from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import Resource


@runtime_checkable
class ResourceRepo(Protocol):
    """Repository contract for resource records."""

    resources: dict[str, Resource]

    def create_resource(self, *, url: str, modality: str, local_path: str) -> Resource: ...

    def load_existing(self) -> None: ...
