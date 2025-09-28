"""
MemU SDK Data Models

Defines request and response models for MemU API interactions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """Individual conversation message"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    time: Optional[str] = Field(None, description="Message time in ISO 8601 format, taking higher priority than session_date")


class MemorizeRequest(BaseModel):
    """Request model for memorize conversation API
    Either conversation_text or conversation must be provided"""

    conversation_text: Optional[str] = Field(
        None, description="Conversation to memorize in plain text format"
    )
    conversation: Optional[list[ConversationMessage]] = Field(
        None, description="Conversation to memorize in role-content format"
    )
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Agent display name")
    session_date: Optional[str] = Field(
        None, description="Session date in ISO 8601 format"
    )


class MemorizeResponse(BaseModel):
    """Response model for memorize conversation API"""

    task_id: str = Field(..., description="Task identifier for tracking")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Response message")


class MemorizeTaskStatusResponse(BaseModel):
    """Response model for memorize task status API"""

    task_id: str = Field(..., description="Task ID")
    status: str = Field(
        ..., description="Task status (e.g., PENDING, SUCCESS, FAILURE)"
    )
    detail_info: str = Field(default="", description="Detail information")


class MemorizeTaskSummaryReadyRequest(BaseModel):
    """Request model for memorize task summary ready API"""
    # user_id: str = Field(..., description="User ID")
    # agent_id: Optional[str] = Field(None, description="Agent ID")
    group: str = Field(default="basic", description="Category group to query")


class MemorizeTaskSummaryReadyResponse(BaseModel):
    """Response model for memorize task summary ready API"""

    all_ready: bool = Field(..., description="Whether all summaries are ready")
    category_ready: dict[str, bool] = Field(..., description="Whether each category is ready")


class ErrorDetail(BaseModel):
    """Error detail model for validation errors"""

    loc: list = Field(..., description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationError(BaseModel):
    """Validation error response model"""

    detail: list[ErrorDetail] = Field(..., description="List of validation errors")


# ========== New Retrieve API Models ==========


class DefaultCategoriesRequest(BaseModel):
    """Request model for default categories API"""

    user_id: str = Field(..., description="User ID")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    want_memory_items: bool = Field(default=False, description="Request also raw memory items")


class MemoryItem(BaseModel):
    """Memory item model"""

    memory_id: str = Field(..., description="Memory identifier")
    category: str = Field(..., description="Memory category")
    content: str = Field(..., description="Memory content")
    happened_at: datetime = Field(..., description="When the memory happened")
    created_at: datetime = Field(..., description="When the memory was created")
    updated_at: datetime = Field(..., description="When the memory was last updated")


class CategoryMemoryItems(BaseModel):
    """Category memory items model"""

    memories: List[MemoryItem] = Field(..., description="Memory items")
    memory_count: int = Field(..., description="Number of memory items")

class CategoryResponse(BaseModel):
    """Category response model"""
    
    name: str = Field(..., description="Category name")
    type: str = Field(..., description="Category type")
    user_id: Optional[str] = Field(None, description="User ID")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    description: str = Field(default="", description="Category description")
    # is_active: bool = Field(..., description="Whether the category is active")
    # memories: Optional[List[MemoryItem] | None] = Field(None, description="Memories in this category")
    # memory_count: Optional[int | None] = Field(None, description="Number of memories in this category")
    memory_items: Optional[CategoryMemoryItems | None] = Field(None, description="Memory items in this category")
    summary: Optional[str | None] = Field(None, description="Memory summarization for this category")


class DefaultCategoriesResponse(BaseModel):
    """Response model for default categories API"""

    categories: List[CategoryResponse] = Field(
        ..., description="List of category objects"
    )
    total_categories: int = Field(..., description="Total number of categories")


class RelatedMemoryItemsRequest(BaseModel):
    """Request model for related memory items API"""

    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(
        None, description="Agent identifier"
    )
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, description="Number of top results to return")
    min_similarity: float = Field(0.3, description="Minimum similarity threshold")
    include_categories: Optional[List[str]] = Field(
        None, description="Categories to include in search"
    )


class RelatedMemory(BaseModel):
    """Related memory with similarity score"""

    memory: MemoryItem = Field(..., description="Memory item")
    user_id: Optional[str] = Field(None, description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    similarity_score: float = Field(..., description="Similarity score")


class RelatedMemoryItemsResponse(BaseModel):
    """Response model for related memory items API"""

    related_memories: List[RelatedMemory] = Field(
        ..., description="List of related memories"
    )
    query: str = Field(..., description="Original search query")
    total_found: int = Field(..., description="Total number of memories found")
    search_params: Dict[str, Any] = Field(..., description="Search parameters used")


class RelatedClusteredCategoriesRequest(BaseModel):
    """Request model for related clustered categories API"""

    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(
        None, description="Agent identifier"
    )
    category_query: str = Field(..., description="Category search query")
    top_k: int = Field(5, description="Number of top categories to return")
    min_similarity: float = Field(0.3, description="Minimum similarity threshold")
    want_summary: bool = Field(default=True, description="Request summary instead of raw memory items")


class ClusteredCategory(BaseModel):
    """Clustered category with memories"""

    name: str = Field(..., description="Category name")
    user_id: Optional[str] = Field(None, description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    similarity_score: float = Field(..., description="Similarity score")
    memories: Optional[List[MemoryItem] | None] = Field(None, description="Memories in this category")
    memory_count: Optional[int | None] = Field(None, description="Number of memories in category")
    summary: Optional[str | None] = Field(None, description="Memory summarization for this category")


class RelatedClusteredCategoriesResponse(BaseModel):
    """Response model for related clustered categories API"""

    clustered_categories: List[ClusteredCategory] = Field(
        ..., description="List of clustered categories"
    )
    category_query: str = Field(..., description="Original category query")
    total_categories_found: int = Field(..., description="Total categories found")
    search_params: Dict[str, Any] = Field(..., description="Search parameters used")


# ========== Delete Memory API Models ==========

class DeleteMemoryRequest(BaseModel):
    """Request model for delete memory API"""

    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier (optional, delete all user memories if not provided)")


class DeleteMemoryResponse(BaseModel):
    """Response model for delete memory API"""

    success: bool = Field(..., description="Operation success status")
    deleted_count: Optional[int] = Field(None, description="Number of memories deleted")


# ========== Chat API Models ==========

class ChatRequest(BaseModel):
    """Request model for chat API"""

    user_id: str = Field(..., description="User identifier")
    user_name: Optional[str] = Field(None, description="User display name")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: Optional[str] = Field(None, description="Agent display name")
    message: str = Field(..., description="User message content")
    system: Optional[str] = Field(None, description="System message content")
    model: Optional[str] = Field(None, description="Chat LLM model")
    # Now configure the maximum context token in the web platform.
    # max_context_tokens: Optional[int] = Field(
    #     None, description="Maximum tokens for final chat prompt (current query + short term context + long term memory), corresponding to ChatTokenUsage.prompt_tokens")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters for LLM")


class ChatTokenUsageBreakdown(BaseModel):
    """Token usage breakdown for chat response"""

    current_query: int = Field(0, description="Tokens used for current query")
    short_term_context: int = Field(0, description="Tokens used for short term context")
    user_profile: int = Field(0, description="Tokens used for user profile")
    retrieved_memory: int = Field(0, description="Tokens used for retrieved memory")


class ChatTokenUsage(BaseModel):
    """Token usage information for chat response"""

    prompt_tokens: int = Field(..., description="Total prompt tokens")
    prompt_tokens_breakdown: Optional[ChatTokenUsageBreakdown] = Field(None, description="Breakdown of prompt tokens")
    completion_tokens: int = Field(..., description="Completion tokens")
    total_tokens: int = Field(..., description="Total tokens")


class ChatResponse(BaseModel):
    """Response model for chat API"""

    message: str = Field(..., description="AI response message")
    chat_token_usage: ChatTokenUsage = Field(..., description="Token usage information")
