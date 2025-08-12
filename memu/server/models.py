"""
Server API Models

Pydantic models for request and response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ========== Memorize API Models ==========

class ConversationMessage(BaseModel):
    """Individual conversation message"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class MemorizeRequest(BaseModel):
    """Request model for memorize API"""
    conversation_text: Optional[str] = Field(
        None, description="Conversation as plain text"
    )
    conversation: Optional[List[ConversationMessage]] = Field(
        None, description="Conversation as structured messages"
    )
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Agent display name")
    session_date: Optional[str] = Field(
        None, description="Session date in ISO format"
    )


class MemorizeResponse(BaseModel):
    """Response model for memorize API"""
    task_id: str = Field(..., description="Task identifier for tracking")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Response message")


class TaskStatusResponse(BaseModel):
    """Response model for task status API"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    detail_info: str = Field(default="", description="Detail information")


# ========== Retrieve API Models ==========

class DefaultCategoriesRequest(BaseModel):
    """Request model for default categories API"""
    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    include_inactive: bool = Field(False, description="Include inactive categories")


class MemoryItem(BaseModel):
    """Memory item model"""
    memory_id: str = Field(..., description="Memory identifier")
    category: str = Field(..., description="Memory category")
    content: str = Field(..., description="Memory content")
    happened_at: datetime = Field(..., description="When the memory happened")
    created_at: Optional[datetime] = Field(None, description="When the memory was created")
    updated_at: Optional[datetime] = Field(None, description="When the memory was updated")


class CategoryInfo(BaseModel):
    """Category information model"""
    name: str = Field(..., description="Category name")
    type: str = Field(..., description="Category type")
    description: str = Field(..., description="Category description")
    is_active: bool = Field(..., description="Whether category is active")
    memories: List[MemoryItem] = Field(..., description="Memories in category")
    memory_count: int = Field(..., description="Number of memories")


class DefaultCategoriesResponse(BaseModel):
    """Response model for default categories API"""
    categories: List[CategoryInfo] = Field(..., description="Categories list")
    total_categories: int = Field(..., description="Total number of categories")


class RelatedMemoryItemsRequest(BaseModel):
    """Request model for related memory items API"""
    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, description="Number of results to return")
    min_similarity: float = Field(0.3, description="Minimum similarity threshold")
    include_categories: Optional[List[str]] = Field(
        None, description="Categories to include in search"
    )


class RelatedMemoryItem(BaseModel):
    """Related memory item with similarity score"""
    memory: MemoryItem = Field(..., description="Memory item")
    similarity_score: float = Field(..., description="Similarity score")


class RelatedMemoryItemsResponse(BaseModel):
    """Response model for related memory items API"""
    related_memories: List[RelatedMemoryItem] = Field(
        ..., description="Related memories list"
    )
    query: str = Field(..., description="Original search query")
    total_found: int = Field(..., description="Total memories found")
    search_params: Dict[str, Any] = Field(..., description="Search parameters")


class RelatedClusteredCategoriesRequest(BaseModel):
    """Request model for related clustered categories API"""
    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    category_query: str = Field(..., description="Category search query")
    top_k: int = Field(5, description="Number of categories to return")
    min_similarity: float = Field(0.3, description="Minimum similarity threshold")


class ClusteredCategory(BaseModel):
    """Clustered category with memories"""
    name: str = Field(..., description="Category name")
    similarity_score: float = Field(..., description="Similarity score")
    memories: List[MemoryItem] = Field(..., description="Category memories")
    memory_count: int = Field(..., description="Number of memories")


class RelatedClusteredCategoriesResponse(BaseModel):
    """Response model for related clustered categories API"""
    clustered_categories: List[ClusteredCategory] = Field(
        ..., description="Clustered categories list"
    )
    category_query: str = Field(..., description="Original category query")
    total_categories_found: int = Field(..., description="Total categories found")
    search_params: Dict[str, Any] = Field(..., description="Search parameters")


# ========== Error Models ==========

class ErrorDetail(BaseModel):
    """Error detail model"""
    loc: List[str] = Field(..., description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    detail: List[ErrorDetail] = Field(..., description="Validation errors")
