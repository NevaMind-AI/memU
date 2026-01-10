"""
MemU SDK Data Models

Pydantic models representing the data structures returned by the MemU Cloud API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskStatusEnum(str, Enum):
    """Status values for asynchronous memorization tasks."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class MemoryResource(BaseModel):
    """
    Represents a raw resource stored in MemU.

    Resources are the source materials (conversations, documents, images, etc.)
    from which memory items are extracted.
    """

    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, description="Unique identifier for the resource")
    url: str | None = Field(default=None, description="URL or path to the resource")
    modality: str | None = Field(
        default=None, description="Type of resource: conversation, document, image, video, audio"
    )
    caption: str | None = Field(default=None, description="Caption or description of the resource")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class MemoryItem(BaseModel):
    """
    Represents a discrete memory unit extracted from resources.

    Memory items are individual pieces of information such as preferences,
    skills, opinions, habits, relationships, etc.
    """

    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, description="Unique identifier for the memory item")
    summary: str | None = Field(default=None, description="Summary or description of the memory")
    content: str | None = Field(default=None, description="Content of the memory item")
    memory_type: str | None = Field(
        default=None, description="Type of memory: preference, skill, opinion, habit, relationship, etc."
    )
    category_id: str | None = Field(default=None, description="ID of the category this item belongs to")
    category_name: str | None = Field(default=None, description="Name of the category this item belongs to")
    resource_id: str | None = Field(default=None, description="ID of the source resource")
    score: float | None = Field(default=None, description="Relevance score (for retrieve results)")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class MemoryCategory(BaseModel):
    """
    Represents an aggregated memory category.

    Categories organize related memory items and provide summaries
    of clustered information (e.g., preferences.md, work_life.md).
    """

    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, description="Unique identifier for the category")
    name: str | None = Field(default=None, description="Category name (e.g., 'preferences', 'work_life')")
    summary: str | None = Field(default=None, description="Summary of the category content")
    description: str | None = Field(default=None, description="Description of the category")
    content: str | None = Field(default=None, description="Content of the category")
    item_count: int | None = Field(default=None, description="Number of items in this category")
    score: float | None = Field(default=None, description="Relevance score (for retrieve results)")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class TaskStatus(BaseModel):
    """
    Status information for an asynchronous memorization task.
    """

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(description="Unique identifier for the task")
    status: TaskStatusEnum = Field(description="Current status of the task")
    progress: float | None = Field(default=None, ge=0, le=100, description="Progress percentage (0-100)")
    message: str | None = Field(default=None, description="Status message or error description")
    result: dict[str, Any] | None = Field(default=None, description="Task result when completed")
    created_at: datetime | None = Field(default=None, description="Task creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class MemorizeResult(BaseModel):
    """
    Result of a memorization operation.

    Contains the task ID for async operations or the full result for
    synchronous operations.
    """

    model_config = ConfigDict(extra="allow")

    task_id: str | None = Field(default=None, description="Task ID for async tracking")
    resource: MemoryResource | dict[str, Any] | None = Field(default=None, description="Created resource")
    items: list[MemoryItem | dict[str, Any]] = Field(default_factory=list, description="Extracted memory items")
    categories: list[MemoryCategory | dict[str, Any]] = Field(
        default_factory=list,
        description="Updated categories",
    )


class RetrieveResult(BaseModel):
    """
    Result of a memory retrieval operation.

    Contains relevant categories, items, and resources matching the query.
    """

    model_config = ConfigDict(extra="allow")

    categories: list[MemoryCategory | dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant categories",
    )
    items: list[MemoryItem | dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant memory items",
    )
    resources: list[MemoryResource | dict[str, Any]] = Field(
        default_factory=list,
        description="Related raw resources",
    )
    next_step_query: str | None = Field(
        default=None,
        description="Rewritten query for follow-up operations",
    )
