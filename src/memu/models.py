from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill"]


class Resource(BaseModel):
    id: str
    url: str
    modality: str
    local_path: str
    caption: str | None = None
    embedding: list[float] | None = None


class MemoryItem(BaseModel):
    id: str
    resource_id: str
    memory_type: MemoryType
    summary: str
    embedding: list[float]


class MemoryCategory(BaseModel):
    id: str
    name: str
    description: str
    embedding: list[float] | None = None
    summary: str | None = None


class CategoryItem(BaseModel):
    item_id: str
    category_id: str
