"""
Memory API Router

FastAPI router for memory-related endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from ..models import (
    MemorizeRequest,
    MemorizeResponse,
    TaskStatusResponse,
    DefaultCategoriesRequest,
    DefaultCategoriesResponse,
    RelatedMemoryItemsRequest,
    RelatedMemoryItemsResponse,
    RelatedClusteredCategoriesRequest,
    RelatedClusteredCategoriesResponse,
)
from ..services.memory_service import MemoryService
from ..services.task_service import TaskService
from ...utils.logging import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Service instances
memory_service = None
task_service = None


def get_memory_service() -> MemoryService:
    """Get memory service instance"""
    global memory_service
    if memory_service is None:
        memory_service = MemoryService()
    return memory_service


def get_task_service() -> TaskService:
    """Get task service instance"""
    global task_service
    if task_service is None:
        task_service = TaskService()
    return task_service


@router.post("/memorize", response_model=MemorizeResponse)
async def memorize_conversation(
    request: MemorizeRequest,
    background_tasks: BackgroundTasks,
    memory_svc: MemoryService = Depends(get_memory_service),
    task_svc: TaskService = Depends(get_task_service),
):
    """
    Start memorization process for conversation data
    
    This endpoint starts a background task to process and memorize conversation data.
    Returns a task ID that can be used to track the progress.
    """
    try:
        logger.info(
            f"Starting memorization for user {request.user_id}, agent {request.agent_id}"
        )
        
        # Validate request
        if not request.conversation_text and not request.conversation:
            raise HTTPException(
                status_code=422,
                detail="Either conversation_text or conversation must be provided"
            )
        
        # Create task
        task_id = task_svc.create_task("memorize", {
            "user_id": request.user_id,
            "user_name": request.user_name,
            "agent_id": request.agent_id,
            "agent_name": request.agent_name,
            "conversation_text": request.conversation_text,
            "conversation": [msg.dict() for msg in request.conversation] if request.conversation else None,
            "session_date": request.session_date or datetime.now().isoformat(),
        })
        
        # Start background task
        background_tasks.add_task(
            _process_memorization_task,
            task_id,
            request,
            memory_svc,
            task_svc
        )
        
        return MemorizeResponse(
            task_id=task_id,
            status="PENDING",
            message="Memorization task started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting memorization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _process_memorization_task(
    task_id: str,
    request: MemorizeRequest,
    memory_svc: MemoryService,
    task_svc: TaskService
):
    """Background task to process memorization"""
    try:
        logger.info(f"Processing memorization task {task_id}")
        
        # Update task status
        task_svc.update_task(task_id, "PROCESSING", None, None)
        
        # Process conversation
        result = await memory_svc.memorize_conversation(
            conversation_text=request.conversation_text,
            conversation=request.conversation,
            user_id=request.user_id,
            user_name=request.user_name,
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            session_date=request.session_date
        )
        
        # Update task with result
        task_svc.update_task(task_id, "SUCCESS", result, None)
        logger.info(f"Memorization task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in memorization task {task_id}: {e}", exc_info=True)
        task_svc.update_task(task_id, "FAILURE", None, str(e))


@router.get("/memorize/status/{task_id}")
async def get_memorization_status(
    task_id: str,
    task_svc: TaskService = Depends(get_task_service),
):
    """
    Get the status of a memorization task
    
    Returns the current status and result of a memorization task.
    """
    try:
        task = task_svc.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatusResponse(
            task_id=task_id,
            status=task["status"],
            result=task.get("result"),
            error=task.get("error"),
            created_at=task["created_at"],
            updated_at=task["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/default-categories", response_model=DefaultCategoriesResponse)
async def retrieve_default_categories(
    request: DefaultCategoriesRequest,
    memory_svc: MemoryService = Depends(get_memory_service),
):
    """
    Retrieve default categories and their content
    
    Returns default memory categories with their stored content.
    """
    try:
        logger.info(f"Retrieving default categories for user {request.user_id}")
        
        result = await memory_svc.retrieve_default_categories(
            user_id=request.user_id,
            agent_id=request.agent_id,
            include_inactive=request.include_inactive
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving default categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/related-memory-items", response_model=RelatedMemoryItemsResponse)
async def retrieve_related_memory_items(
    request: RelatedMemoryItemsRequest,
    memory_svc: MemoryService = Depends(get_memory_service),
):
    """
    Retrieve related memory items using semantic search
    
    Returns memory items that are semantically related to the query.
    """
    try:
        logger.info(
            f"Retrieving related memory items for user {request.user_id}, query: '{request.query}'"
        )
        
        result = await memory_svc.retrieve_related_memory_items(
            user_id=request.user_id,
            agent_id=request.agent_id,
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            include_categories=request.include_categories
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving related memory items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/related-clustered-categories", response_model=RelatedClusteredCategoriesResponse)
async def retrieve_related_clustered_categories(
    request: RelatedClusteredCategoriesRequest,
    memory_svc: MemoryService = Depends(get_memory_service),
):
    """
    Retrieve related clustered categories using semantic search
    
    Returns categories that are semantically related to the category query.
    """
    try:
        logger.info(
            f"Retrieving clustered categories for user {request.user_id}, query: '{request.category_query}'"
        )
        
        result = await memory_svc.retrieve_related_clustered_categories(
            user_id=request.user_id,
            agent_id=request.agent_id,
            category_query=request.category_query,
            top_k=request.top_k,
            min_similarity=request.min_similarity
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving clustered categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
