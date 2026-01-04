from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import Resource


@runtime_checkable
class ResourceRepo(Protocol):
    """Repository contract for resource records."""

    resources: dict[str, Resource]

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]: ...

    def create_resource(
        self,
        *,
        url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        user_data: dict[str, Any],
    ) -> Resource: ...

    def load_existing(self) -> None: ...
