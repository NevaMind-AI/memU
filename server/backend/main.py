"""
MemU Backend Management System - FastAPI Backend

Provides API interfaces for conversation, memory and memory operation records in the database
"""

import json
import os
import sys
import time
import traceback
import uvicorn
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for MemU imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from memu.config import get_llm_config_manager
from memu.db import build_connection_string, get_database_manager
from memu.llm import OpenAIClient
from memu.memory.base import Memory
from memu.memory.manager import MemoryClient
from memu.memory.pipeline import MemoryUpdatePipeline
from memu.memo.manager import ConversationManager
from memu.utils import get_logger

logger = get_logger(__name__)


def setup_postgres_env():
    """Set PostgreSQL environment variables"""
    # Get default configuration from setup script
    default_config = {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'memu',
        'POSTGRES_USER': 'chenhong',
        'POSTGRES_PASSWORD': ''
    }
    
    # Only set default values when environment variables are not set
    for key, value in default_config.items():
        if not os.getenv(key):
            os.environ[key] = value
    
    logger.info("PostgreSQL Configuration:")
    logger.info(f"   POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
    logger.info(f"   POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}")
    logger.info(f"   POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
    logger.info(f"   POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
    logger.info(f"   POSTGRES_PASSWORD: {'*' * len(os.getenv('POSTGRES_PASSWORD', ''))}")


# Set environment variables
setup_postgres_env()

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Cached configuration functions
@lru_cache(maxsize=1)
def get_cached_llm_config():
    """Get cached LLM configuration."""
    config_manager = get_llm_config_manager()
    return config_manager.get_provider_config("openai")

@lru_cache(maxsize=1)
def get_cached_db_config():
    """Get cached database configuration."""
    return build_connection_string()

# Initialize FastAPI app
app = FastAPI(
    title="MemU Backend Management System",
    description="Provides API interfaces for conversation, memory and memory operation records in the database",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
db_manager = get_database_manager()
# Create a direct database memory client for the API endpoints
memory_database = db_manager.get_memory_db()
conversation_manager = ConversationManager(db_manager=db_manager, enable_embeddings=True)


# Pydantic models
class SystemStats(BaseModel):
    conversations: Dict[str, int]
    memories: Dict[str, int]
    agents: Dict[str, int]
    users: Dict[str, int]


class ConversationInfo(BaseModel):
    conversation_id: str
    agent_id: str
    user_id: str
    created_at: datetime
    turn_count: Optional[int] = 0
    session_id: Optional[str] = None
    memory_id: Optional[str] = None


class MemoryInfo(BaseModel):
    memory_id: str
    agent_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class MemoryOperation(BaseModel):
    operation_id: str
    memory_id: str
    agent_id: str
    user_id: str
    operation_type: str
    timestamp: datetime
    details: str


class DeleteResponse(BaseModel):
    success: bool
    message: str


class UpdateConversationRequest(BaseModel):
    agent_id: str
    user_id: str
    conversation: List[Dict[str, str]]


class UpdateProfileRequest(BaseModel):
    agent_id: str
    user_id: str
    profile_info: str


class UpdateEventsRequest(BaseModel):
    agent_id: str
    user_id: str
    events: List[str]


class SaveConversationRequest(BaseModel):
    agent_id: str
    user_id: str
    messages: List[Dict[str, str]]
    session_id: Optional[str] = None
    memory_id: Optional[str] = None


# API routes
@app.get("/", response_model=Dict[str, str])
async def root():
    """Health check"""
    return {"message": "MemU Backend Management System API", "status": "running"}


@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """Get system statistics"""
    try:
        stats = get_system_stats()
        return SystemStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations", response_model=List[ConversationInfo])
async def get_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get conversation list"""
    try:
        # Get conversation list
        conversations_data = []
        
        if agent_id:
            conversations_data = conversation_manager.get_conversation_history(
                agent_id=agent_id, 
                limit=per_page * page,
                user_id=user_id if user_id else None
            )
        else:
            conversations_data = get_all_conversations(limit=per_page * page)
        
        # Pagination handling
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_conversations = conversations_data[start_idx:end_idx]
        
        return [ConversationInfo(**conv) for conv in paginated_conversations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: str):
    """Get conversation details"""
    try:
        conversation = conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return {
            "conversation_id": conversation.conversation_id,
            "agent_id": conversation.agent_id,
            "user_id": conversation.user_id,
            "created_at": conversation.created_at,
            "turn_count": conversation.turn_count,
            "session_id": conversation.session_id,
            "memory_id": conversation.memory_id,
            "messages": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "message_index": msg.message_index,
                    "created_at": msg.created_at
                }
                for msg in conversation.messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}", response_model=DeleteResponse)
async def delete_conversation(conversation_id: str):
    """Delete conversation"""
    try:
        success = conversation_manager.delete_conversation(conversation_id)
        if success:
            return DeleteResponse(success=True, message="Conversation deleted successfully")
        else:
            return DeleteResponse(success=False, message="Deletion failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memories", response_model=List[MemoryInfo])
async def get_memories(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get memory list"""
    try:
        memories_data = get_all_memories(agent_id=agent_id or '', user_id=user_id or '', limit=per_page * page)
        
        # Pagination handling
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_memories = memories_data[start_idx:end_idx]
        
        return [MemoryInfo(**memory) for memory in paginated_memories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memories/{memory_id}")
async def get_memory_detail(memory_id: str):
    """Get memory details"""
    try:
        memory = memory_database.load_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        # Safe access to memory methods and attributes
        try:
            profile_content = memory.get_profile() if hasattr(memory, 'get_profile') else []
            if profile_content and isinstance(profile_content, list):
                profile_str = "\n".join(str(item) for item in profile_content)
            else:
                profile_str = str(profile_content) if profile_content else ""
        except Exception as e:
            logger.warning(f"Error getting profile content: {e}")
            profile_str = ""
        
        try:
            event_content = memory.get_events() if hasattr(memory, 'get_events') else []
        except Exception as e:
            logger.warning(f"Error getting event content: {e}")
            event_content = []
        
        try:
            mind_content = memory.get_mind() if hasattr(memory, 'get_mind') else []
        except Exception as e:
            logger.warning(f"Error getting mind content: {e}")
            mind_content = []
        
        return {
            'memory_id': memory.memory_id,
            'agent_id': memory.agent_id,
            'user_id': memory.user_id,
            'created_at': memory.created_at,
            'updated_at': memory.updated_at,
            'profile_content': profile_str,
            'event_content': event_content,
            'mind_content': mind_content,
            # mind_metadata removed (legacy compatibility eliminated)
        }
    except Exception as e:
        logger.error(f"Error getting memory detail for {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memories/{memory_id}", response_model=DeleteResponse)
async def delete_memory(memory_id: str):
    """Delete memory"""
    try:
        success = memory_database.delete_memory(memory_id)
        if success:
            return DeleteResponse(success=True, message="Memory deleted successfully")
        else:
            return DeleteResponse(success=False, message="Deletion failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversations/save")
async def save_conversation(request: SaveConversationRequest):
    """Save conversation to database"""
    try:
        # Use the conversation manager to save conversation
        conversation = conversation_manager.record_conversation(
            agent_id=request.agent_id,
            user_id=request.user_id,
            messages=request.messages,
            session_id=request.session_id,
            memory_id=request.memory_id,
            enable_vectorization=True
        )
        
        logger.info(f"Saved conversation {conversation.conversation_id} for {request.agent_id}/{request.user_id}")
        
        return {
            "success": True, 
            "message": "Conversation saved successfully",
            "conversation_id": conversation.conversation_id,
            "session_id": conversation.session_id,
            "created_at": conversation.created_at.isoformat(),
            "message_count": len(conversation.messages)
        }
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/memories/update-memory")
async def update_memory_with_conversation(request: UpdateConversationRequest):
    """Update memory with conversation data using MemoryUpdatePipeline"""
    start_time = time.time()
    
    # Log incoming request details
    logger.info(f"[MEMORY_UPDATE] Starting memory update for agent_id={request.agent_id}, user_id={request.user_id}")
    logger.info(f"[MEMORY_UPDATE] Conversation contains {len(request.conversation)} turns")
    
    try:
        # Get or create memory using direct database access
        memory_lookup_start = time.time()
        existing_memory = memory_database.get_memory_by_agent(request.agent_id, request.user_id)
        memory_lookup_time = time.time() - memory_lookup_start
        
        if existing_memory:
            memory = existing_memory
            logger.info(f"[MEMORY_UPDATE] Found existing memory (ID: {memory.memory_id}) in {memory_lookup_time:.3f}s")
            
            # Log current memory state
            current_profile = memory.get_profile() if hasattr(memory, 'get_profile') else []
            current_events = memory.get_events() if hasattr(memory, 'get_events') else []
            current_mind = memory.get_mind() if hasattr(memory, 'get_mind') else []
            
            logger.info(f"[MEMORY_UPDATE] Current memory state - Profile items: {len(current_profile)}, Events: {len(current_events)}, Mind insights: {len(current_mind)}")
        else:
            # Create a new memory if none exists
            memory = Memory(
                agent_id=request.agent_id,
                user_id=request.user_id,
                memory_client=None
            )
            memory_database.save_memory(memory)
            logger.info(f"[MEMORY_UPDATE] Created new memory (ID: {memory.memory_id}) in {memory_lookup_time:.3f}s")
            
            # Initialize empty current state for new memory
            current_profile = []
            current_events = []
            current_mind = []
        
        # Initialize MemoryUpdatePipeline
        try:
            # Try to create OpenAI client for pipeline
            config_start = time.time()
            openai_config = get_cached_llm_config()
            config_time = time.time() - config_start
            
            logger.info(f"[MEMORY_UPDATE] Retrieved LLM config in {config_time:.3f}s")
            
            if openai_config.get("api_key"):
                # Log config parameters (safely)
                safe_config = {k: v for k, v in openai_config.items() if k != "api_key"}
                safe_config["api_key"] = "***REDACTED***"
                logger.info(f"[MEMORY_UPDATE] OpenAI config loaded: {safe_config}")
                
                # Keep only the most basic parameters that OpenAI client needs
                filtered_config = {}
                if openai_config.get("api_key"):
                    filtered_config["api_key"] = openai_config["api_key"]
                if openai_config.get("base_url"):
                    filtered_config["base_url"] = openai_config["base_url"]
                if openai_config.get("model"):
                    filtered_config["model"] = openai_config["model"]
                
                logger.info(f"[MEMORY_UPDATE] Using filtered config with model: {filtered_config.get('model', 'default')}")
                
                try:
                    client_start = time.time()
                    llm_client = OpenAIClient(**filtered_config)
                    client_time = time.time() - client_start
                    logger.info(f"[MEMORY_UPDATE] OpenAI client created successfully in {client_time:.3f}s")
                except Exception as client_error:
                    logger.error(f"[MEMORY_UPDATE] Error creating OpenAI client: {client_error}")
                    logger.error(f"[MEMORY_UPDATE] Attempted config: {filtered_config}")
                    raise client_error
                
                try:
                    pipeline_start = time.time()
                    pipeline = MemoryUpdatePipeline(llm_client=llm_client)
                    pipeline_time = time.time() - pipeline_start
                    logger.info(f"[MEMORY_UPDATE] Pipeline created successfully in {pipeline_time:.3f}s")
                except Exception as pipeline_error:
                    logger.error(f"[MEMORY_UPDATE] Error creating pipeline: {pipeline_error}")
                    raise pipeline_error
                
                # Convert conversation format to match pipeline expectations
                conversion_start = time.time()
                session_conversation = []
                for i, conv in enumerate(request.conversation):
                    user_message = conv.get("user_message", "")
                    ai_response = conv.get("ai_response", "")
                    
                    if user_message:
                        session_conversation.append({"role": "user", "content": user_message})
                        logger.debug(f"[MEMORY_UPDATE] Turn {i+1} - User message: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
                    if ai_response:
                        session_conversation.append({"role": "assistant", "content": ai_response})
                        logger.debug(f"[MEMORY_UPDATE] Turn {i+1} - AI response: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}")
                
                conversion_time = time.time() - conversion_start
                logger.info(f"[MEMORY_UPDATE] Converted {len(request.conversation)} conversation turns to {len(session_conversation)} messages in {conversion_time:.3f}s")
                
                # Process through pipeline
                try:
                    pipeline_processing_start = time.time()
                    logger.info(f"[MEMORY_UPDATE] Starting pipeline processing with {len(session_conversation)} messages")
                    
                    updated_memory, pipeline_result = pipeline.update_with_pipeline(memory, session_conversation)
                    
                    pipeline_processing_time = time.time() - pipeline_processing_start
                    logger.info(f"[MEMORY_UPDATE] Pipeline processing completed successfully in {pipeline_processing_time:.3f}s")
                    
                    # Log pipeline results
                    logger.info(f"[MEMORY_UPDATE] Pipeline results:")
                    logger.info(f"  - Profile updated: {pipeline_result.update_result.profile_updated}")
                    logger.info(f"  - Modification stage: {len(pipeline_result.modification_result)} chars")
                    logger.info(f"  - Mind insights: {len(pipeline_result.mind_result.insights)} chars")
                    logger.info(f"  - Confidence score: {pipeline_result.mind_result.confidence_score}")
                    
                    # Log memory changes
                    new_profile = updated_memory.get_profile() if hasattr(updated_memory, 'get_profile') else []
                    new_events = updated_memory.get_events() if hasattr(updated_memory, 'get_events') else []
                    new_mind = updated_memory.get_mind() if hasattr(updated_memory, 'get_mind') else []
                    
                    logger.info(f"[MEMORY_UPDATE] Memory changes:")
                    logger.info(f"  - Profile items: {len(current_profile) if existing_memory else 0} -> {len(new_profile)}")
                    logger.info(f"  - Events: {len(current_events) if existing_memory else 0} -> {len(new_events)}")
                    logger.info(f"  - Mind insights: {len(current_mind) if existing_memory else 0} -> {len(new_mind)}")
                    
                except Exception as pipeline_run_error:
                    logger.error(f"[MEMORY_UPDATE] Error during pipeline processing: {pipeline_run_error}")
                    logger.error(f"[MEMORY_UPDATE] Full traceback: {traceback.format_exc()}")
                    raise pipeline_run_error
                
                # Save the updated memory
                save_start = time.time()
                memory_database.save_memory(updated_memory)
                save_time = time.time() - save_start
                
                total_time = time.time() - start_time
                logger.info(f"[MEMORY_UPDATE] Memory saved to database in {save_time:.3f}s")
                logger.info(f"[MEMORY_UPDATE] Total processing time: {total_time:.3f}s")
                logger.info(f"[MEMORY_UPDATE] Successfully updated memory for {request.agent_id}/{request.user_id}")
                
                return {
                    "success": True, 
                    "message": f"Memory updated via pipeline", 
                    "pipeline_metadata": pipeline_result.pipeline_metadata,
                    "processing_time": total_time,
                    "memory_changes": {
                        "profile_items": len(new_profile),
                        "events": len(new_events),
                        "mind_insights": len(new_mind)
                    }
                }
            else:
                # Fallback to simple processing if no LLM available
                logger.warning("[MEMORY_UPDATE] No OpenAI API key found, falling back to simple event processing")
                raise Exception("No LLM client available")
                
        except Exception as llm_error:
            logger.error(f"[MEMORY_UPDATE] LLM processing failed: {llm_error}")
            return {"success": False, "message": f"LLM processing failed: {llm_error}"}
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[MEMORY_UPDATE] Error updating memory with conversation after {total_time:.3f}s: {e}")
        logger.error(f"[MEMORY_UPDATE] Full error traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


@app.post("/api/memories/update-profile")
async def update_memory_profile(request: UpdateProfileRequest):
    """Update memory profile information"""
    try:
        # Get or create memory using direct database access
        existing_memory = memory_database.get_memory_by_agent(request.agent_id, request.user_id)
        if existing_memory:
            memory = existing_memory
        else:
            # Create a new memory if none exists
            memory = Memory(
                agent_id=request.agent_id,
                user_id=request.user_id,
                memory_client=None
            )
        
        # Add profile information
        current_profile = memory.get_profile()
        updated_profile = current_profile + [request.profile_info]
        memory.profile_content = updated_profile
        
        # Save the updated memory
        memory_database.save_memory(memory)
        
        logger.info(f"Updated profile for {request.agent_id}/{request.user_id}")
        return {"success": True, "message": "Profile updated"}
    except Exception as e:
        logger.error(f"Error updating memory profile: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


@app.post("/api/memories/update-events")
async def update_memory_events(request: UpdateEventsRequest):
    """Update memory events"""
    try:
        # Get or create memory using direct database access
        existing_memory = memory_database.get_memory_by_agent(request.agent_id, request.user_id)
        if existing_memory:
            memory = existing_memory
        else:
            # Create a new memory if none exists
            memory = Memory(
                agent_id=request.agent_id,
                user_id=request.user_id,
                memory_client=None
            )
        
        # Add events
        current_events = memory.get_events()
        updated_events = current_events + request.events
        memory.event_content = updated_events
        
        # Save the updated memory
        memory_database.save_memory(memory)
        
        logger.info(f"Updated events for {request.agent_id}/{request.user_id}, added {len(request.events)} events")
        return {"success": True, "message": f"Events updated, {len(request.events)} events added"}
    except Exception as e:
        logger.error(f"Error updating memory events: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/memories/stats/{agent_id}")
async def get_memory_stats(agent_id: str):
    """Get memory statistics for an agent"""
    try:
        # Get basic memory count
        memories_data = get_all_memories(agent_id=agent_id, user_id='', limit=1000)
        memory_count = len(memories_data)
        
        # Get user count for this agent
        users_data = get_unique_users()
        agent_users = [user for user in users_data if any(
            memory.get('agent_id') == agent_id 
            for memory in memories_data 
            if memory.get('user_id') == user
        )]
        
        return {
            "agent_id": agent_id,
            "memory_count": memory_count,
            "user_count": len(agent_users),
            "users": agent_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory-operations", response_model=List[MemoryOperation])
async def get_memory_operations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """Get memory operation records"""
    try:
        operations = get_memory_operations(limit=per_page * page)
        
        # Pagination handling
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_operations = operations[start_idx:end_idx]
        
        return [MemoryOperation(**op) for op in paginated_operations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents", response_model=List[str])
async def get_agents():
    """Get list of all agents"""
    try:
        agents = get_unique_agents()
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users", response_model=List[str])
async def get_users():
    """Get list of all users"""
    try:
        users = get_unique_users()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Utility functions
def get_db_connection_string() -> Optional[str]:
    """Get database connection string from environment"""
    try:
        return get_cached_db_config()
    except Exception as e:
        logger.error(f"Error building connection string: {e}")
        return None


def get_system_stats():
    """Get system statistics"""
    try:
        connection_string = get_db_connection_string()
        if not connection_string:
            return {
                "conversations": {"total": 0, "today": 0, "this_week": 0, "this_month": 0},
                "memories": {"total": 0, "today": 0, "this_week": 0, "this_month": 0},
                "agents": {"total": 0, "active_today": 0, "active_this_week": 0, "active_this_month": 0},
                "users": {"total": 0, "active_today": 0, "active_this_week": 0, "active_this_month": 0}
            }
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Get conversation statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN created_at >= CURRENT_DATE THEN 1 END) as today,
                        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as this_week,
                        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as this_month
                    FROM conversations
                """)
                conv_stats = cur.fetchone()
                
                # Get memory statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN updated_at >= CURRENT_DATE THEN 1 END) as today,
                        COUNT(CASE WHEN updated_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as this_week,
                        COUNT(CASE WHEN updated_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as this_month
                    FROM memories
                """)
                mem_stats = cur.fetchone()
                
                # Get agent statistics
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT agent_id) as total,
                        COUNT(DISTINCT CASE WHEN updated_at >= CURRENT_DATE THEN agent_id END) as active_today,
                        COUNT(DISTINCT CASE WHEN updated_at >= CURRENT_DATE - INTERVAL '7 days' THEN agent_id END) as active_this_week,
                        COUNT(DISTINCT CASE WHEN updated_at >= CURRENT_DATE - INTERVAL '30 days' THEN agent_id END) as active_this_month
                    FROM memories
                """)
                agent_stats = cur.fetchone()
                
                # Get user statistics
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT user_id) as total,
                        COUNT(DISTINCT CASE WHEN updated_at >= CURRENT_DATE THEN user_id END) as active_today,
                        COUNT(DISTINCT CASE WHEN updated_at >= CURRENT_DATE - INTERVAL '7 days' THEN user_id END) as active_this_week,
                        COUNT(DISTINCT CASE WHEN updated_at >= CURRENT_DATE - INTERVAL '30 days' THEN user_id END) as active_this_month
                    FROM memories
                """)
                user_stats = cur.fetchone()
                
                return {
                    "conversations": dict(conv_stats),
                    "memories": dict(mem_stats),
                    "agents": dict(agent_stats),
                    "users": dict(user_stats)
                }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "conversations": {"total": 0, "today": 0, "this_week": 0, "this_month": 0},
            "memories": {"total": 0, "today": 0, "this_week": 0, "this_month": 0},
            "agents": {"total": 0, "active_today": 0, "active_this_week": 0, "active_this_month": 0},
            "users": {"total": 0, "active_today": 0, "active_this_week": 0, "active_this_month": 0}
        }


def get_all_conversations(limit=100):
    """Get basic information of all conversations"""
    try:
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT conversation_id, agent_id, user_id, created_at, 
                           session_id, memory_id
                    FROM conversations 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return []


def get_all_memories(agent_id='', user_id='', limit=100):
    """Get basic information of all memories"""
    try:
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Build query with optional filters
                query = """
                    SELECT memory_id, agent_id, user_id, created_at, updated_at
                    FROM memories
                """
                params = []
                conditions = []
                
                if agent_id:
                    conditions.append("agent_id = %s")
                    params.append(agent_id)
                
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY updated_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        return []


def get_memory_operations(limit=100):
    """Get memory operation records"""
    try:
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT memory_id, agent_id, user_id, updated_at, created_at,
                           CASE 
                               WHEN created_at = updated_at THEN 'CREATE'
                               ELSE 'UPDATE'
                           END as operation_type
                    FROM memories 
                    ORDER BY updated_at DESC 
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                
                operations = []
                for row in rows:
                    operations.append({
                        'operation_id': f"{row['memory_id']}_{int(row['updated_at'].timestamp())}",
                        'memory_id': row['memory_id'],
                        'agent_id': row['agent_id'],
                        'user_id': row['user_id'],
                        'operation_type': row['operation_type'],
                        'timestamp': row['updated_at'],
                        'details': f"Memory {row['operation_type'].lower()}d"
                    })
                
                return operations
    except Exception as e:
        logger.error(f"Error getting memory operations: {e}")
        return []


def get_unique_agents():
    """Get list of unique agents"""
    try:
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT agent_id FROM memories ORDER BY agent_id")
                rows = cur.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error getting unique agents: {e}")
        return []


def get_unique_users():
    """Get list of unique users"""
    try:
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT user_id FROM memories ORDER BY user_id")
                rows = cur.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error getting unique users: {e}")
        return []


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 