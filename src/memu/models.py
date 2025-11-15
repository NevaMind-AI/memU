from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MemoryType = Literal["profile", "event", "knowledge", "behavior"]


class Resource(BaseModel):
    id: str
    url: str
    modality: str
    local_path: str
    caption: str | None = None
    caption_embedding: list[float] | None = None


class MemoryItem(BaseModel):
    id: str
    resource_id: str
    memory_type: MemoryType
    summary: str
    embedding: list[float]
    category_ids: list[str] = Field(default_factory=list)


class MemoryCategory(BaseModel):
    id: str
    name: str
    description: str
    embedding: list[float] | None = None
    summary: str | None = None


class CategoryItem(BaseModel):
    item_id: str
    category_id: str
