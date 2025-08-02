"""
MemU SDK Data Models

Defines request and response models for MemU API interactions.
"""

from typing import Optional
from pydantic import BaseModel, Field


class MemorizeRequest(BaseModel):
    """Request model for memorize conversation API"""
    
    conversation_text: str = Field(..., description="Conversation text to memorize")
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Agent display name")
    api_key_id: str = Field(..., description="API key identifier")
    project_id: str = Field(..., description="Project identifier")


class MemorizeResponse(BaseModel):
    """Response model for memorize conversation API"""
    
    task_id: str = Field(..., description="Celery task ID for tracking")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Response message")


class ErrorDetail(BaseModel):
    """Error detail model for validation errors"""
    
    loc: list = Field(..., description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationError(BaseModel):
    """Validation error response model"""
    
    detail: list[ErrorDetail] = Field(..., description="List of validation errors")