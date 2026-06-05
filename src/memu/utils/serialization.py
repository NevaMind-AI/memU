from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def model_dump_without_embeddings(obj: BaseModel) -> dict[str, Any]:
    """Dump a Pydantic model into a JSON-safe public response shape."""

    return obj.model_dump(mode="json", exclude={"embedding"})


__all__ = ["model_dump_without_embeddings"]
