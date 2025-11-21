from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

MemoryType = Literal["profile", "event", "knowledge", "behavior"]


class Resource(BaseModel):
    id: str
    user_id: str
    agent_id: str
    url: str
    modality: str
    local_path: str
    caption: str | None = None
    embedding: list[float] | None = None
    created_at: float | None = None  # timestamp


class MemoryItem(BaseModel):
    id: str
    user_id: str
    agent_id: str
    resource_id: str
    memory_type: MemoryType
    summary: str
    embedding: list[float]
    created_at: float | None = None  # timestamp


class MemoryCategory(BaseModel):
    id: str
    user_id: str
    agent_id: str
    name: str
    description: str
    embedding: list[float] | None = None
    summary: str | None = None
    created_at: float | None = None  # timestamp


class CategoryItem(BaseModel):
    item_id: str
    category_id: str
    user_id: str
    agent_id: str
