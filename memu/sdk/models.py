"""
MemU SDK Data Models

Defines request and response models for MemU API interactions.
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class MemorizeRequest(BaseModel):
    """Request model for memorize conversation API"""
    
    conversation_text: str = Field(..., description="Conversation text to memorize")
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Agent display name")


class MemorizeResponse(BaseModel):
    """Response model for memorize conversation API"""
    
    task_id: str = Field(..., description="Celery task ID for tracking")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Response message")


class MemorizeTaskStatusResponse(BaseModel):
    """Response model for memorize task status API"""
    
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status (e.g., PENDING, SUCCESS, FAILURE)")
    progress: Optional[Dict[str, Any]] = Field(None, description="Task progress information")
    result: Optional[Dict[str, Any]] = Field(None, description="Task results if completed")
    error: Optional[str] = Field(None, description="Error message if task failed")
    started_at: Optional[str] = Field(None, description="Task start timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")


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
    
    project_id: str = Field(..., description="Project identifier")
    include_inactive: bool = Field(False, description="Include inactive categories")


class DefaultCategoriesResponse(BaseModel):
    """Response model for default categories API"""
    
    categories: List[Dict[str, Any]] = Field(..., description="List of category objects")
    total_categories: int = Field(..., description="Total number of categories")
    project_id: str = Field(..., description="Project identifier")


class RelatedMemoryItemsRequest(BaseModel):
    """Request model for related memory items API"""
    
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, description="Number of top results to return")
    min_similarity: float = Field(0.3, description="Minimum similarity threshold")
    include_categories: Optional[List[str]] = Field(None, description="Categories to include in search")


class MemoryItem(BaseModel):
    """Memory item model"""
    
    id: str = Field(..., description="Memory item ID")
    agent_id: str = Field(..., description="Agent identifier")
    user_id: str = Field(..., description="User identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    memory_id: str = Field(..., description="Memory identifier")
    category: str = Field(..., description="Memory category")
    content: str = Field(..., description="Memory content")
    links: List[str] = Field(..., description="Related memory links")
    happened_at: datetime = Field(..., description="When the memory happened")
    created_at: datetime = Field(..., description="When the memory was created")
    updated_at: datetime = Field(..., description="When the memory was last updated")


class RelatedMemory(BaseModel):
    """Related memory with similarity score"""
    
    memory: MemoryItem = Field(..., description="Memory item")
    similarity_score: float = Field(..., description="Similarity score")


class RelatedMemoryItemsResponse(BaseModel):
    """Response model for related memory items API"""
    
    related_memories: List[RelatedMemory] = Field(..., description="List of related memories")
    query: str = Field(..., description="Original search query")
    total_found: int = Field(..., description="Total number of memories found")
    search_params: Dict[str, Any] = Field(..., description="Search parameters used")


class RelatedClusteredCategoriesRequest(BaseModel):
    """Request model for related clustered categories API"""
    
    user_id: str = Field(..., description="User identifier")
    category_query: str = Field(..., description="Category search query")
    top_k: int = Field(5, description="Number of top categories to return")
    min_similarity: float = Field(0.3, description="Minimum similarity threshold")


class ClusteredCategory(BaseModel):
    """Clustered category with memories"""
    
    category_name: str = Field(..., description="Category name")
    similarity_score: float = Field(..., description="Similarity score")
    memories: List[MemoryItem] = Field(..., description="Memories in this category")
    memory_count: int = Field(..., description="Number of memories in category")


class RelatedClusteredCategoriesResponse(BaseModel):
    """Response model for related clustered categories API"""
    
    clustered_categories: List[ClusteredCategory] = Field(..., description="List of clustered categories")
    category_query: str = Field(..., description="Original category query")
    total_categories_found: int = Field(..., description="Total categories found")
    search_params: Dict[str, Any] = Field(..., description="Search parameters used")