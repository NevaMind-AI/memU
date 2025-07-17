"""
MemU Backend Management System - Enhanced FastAPI Backend

Provides API interfaces for both database and file-based memory management:
- Original database-based conversation and memory operations  
- New file-based memory management with 6 memory types
- Conversation analysis and automatic memory extraction
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

# Import new file-based memory API
from file_memory_api import file_memory_router

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
    description="Enhanced API with both database and file-based memory management",
    version="2.0.0"
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


# ================================
# Pydantic Models (existing)
# ================================

class SystemStats(BaseModel):
    conversations: Dict[str, int]
    memories: Dict[str, int]
    agents: Dict[str, int]
    users: Dict[str, int]
    # Add file-based memory stats
    file_memories: Dict[str, int] = {}


class ConversationInfo(BaseModel):
    conversation_id: str
    agent_id: str
    user_id: str
    created_at: str
    turn_count: int
    session_id: Optional[str] = None
    memory_id: Optional[str] = None


class MemoryInfo(BaseModel):
    memory_id: str
    agent_id: str
    user_id: str
    created_at: str
    updated_at: str
    profile_count: int
    event_count: int
    mind_count: int
    total_size: int


class ConversationMessage(BaseModel):
    role: str
    content: str
    message_index: int


class SaveConversationRequest(BaseModel):
    agent_id: str
    user_id: str
    messages: List[ConversationMessage]
    session_id: Optional[str] = None
    memory_id: Optional[str] = None


class ConversationTurn(BaseModel):
    user_message: str
    ai_response: str


class UpdateConversationRequest(BaseModel):
    agent_id: str
    user_id: str
    conversation: List[ConversationTurn]


class DeleteResponse(BaseModel):
    success: bool
    message: str


class MemoryOperation(BaseModel):
    operation_id: str
    memory_id: str
    operation_type: str
    created_at: str
    details: Optional[Dict] = None


# ================================
# Enhanced System Stats
# ================================

def get_system_stats():
    """Get enhanced system statistics including file-based memory"""
    try:
        conn = psycopg2.connect(get_cached_db_config())
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Database stats
        stats = {
            "conversations": {"total": 0, "last_24h": 0},
            "memories": {"total": 0, "last_24h": 0},
            "agents": {"total": 0, "active": 0},
            "users": {"total": 0, "active": 0},
            "file_memories": {"total_characters": 0, "total_files": 0, "total_size": 0}
        }
        
        # Get conversation stats
        cursor.execute("SELECT COUNT(*) as total FROM conversations")
        stats["conversations"]["total"] = cursor.fetchone()["total"]
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM conversations 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        stats["conversations"]["last_24h"] = cursor.fetchone()["count"]
        
        # Get memory stats
        cursor.execute("SELECT COUNT(*) as total FROM memories")
        stats["memories"]["total"] = cursor.fetchone()["total"]
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM memories 
            WHERE updated_at >= NOW() - INTERVAL '24 hours'
        """)
        stats["memories"]["last_24h"] = cursor.fetchone()["count"]
        
        # Get agent stats
        cursor.execute("SELECT COUNT(DISTINCT agent_id) as total FROM conversations")
        stats["agents"]["total"] = cursor.fetchone()["total"]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT agent_id) as count FROM conversations 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        stats["agents"]["active"] = cursor.fetchone()["count"]
        
        # Get user stats
        cursor.execute("SELECT COUNT(DISTINCT user_id) as total FROM conversations")
        stats["users"]["total"] = cursor.fetchone()["total"]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as count FROM conversations 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        stats["users"]["active"] = cursor.fetchone()["count"]
        
        conn.close()
        
        # Get file-based memory stats
        try:
            from memu import MemoryFileManager
            memory_dir = os.getenv("MEMORY_DIR", "memory")
            fm = MemoryFileManager(memory_dir)
            characters = fm.list_characters()
            
            total_files = 0
            total_size = 0
            
            for character in characters:
                char_info = fm.get_character_info(character)
                for memory_type in fm.MEMORY_TYPES:
                    if char_info.get(f"has_{memory_type}", False):
                        total_files += 1
                        total_size += char_info.get(f"{memory_type}_size", 0)
            
            stats["file_memories"] = {
                "total_characters": len(characters),
                "total_files": total_files,
                "total_size": total_size
            }
        except Exception as e:
            logger.warning(f"Could not get file memory stats: {e}")
        
        return stats
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "conversations": {"total": 0, "last_24h": 0},
            "memories": {"total": 0, "last_24h": 0},
            "agents": {"total": 0, "active": 0},
            "users": {"total": 0, "active": 0},
            "file_memories": {"total_characters": 0, "total_files": 0, "total_size": 0}
        }


# ================================
# API routes (existing endpoints)
# ================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Health check"""
    return {
        "message": "MemU Backend Management System API", 
        "status": "running",
        "version": "2.0.0",
        "features": ["database_memory", "file_memory", "conversation_analysis"]
    }


@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """Get enhanced system statistics"""
    try:
        stats = get_system_stats()
        return SystemStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Include File Memory Router
# ================================

# Include the file-based memory API endpoints
app.include_router(file_memory_router)


# ================================
# Storage Mode Selection
# ================================

@app.get("/api/storage/modes")
async def get_storage_modes():
    """Get available storage modes and current configuration"""
    try:
        from memu import MemoryFileManager
        
        # Check database availability
        db_available = True
        try:
            conn = psycopg2.connect(get_cached_db_config())
            conn.close()
        except Exception:
            db_available = False
        
        # Check file storage availability
        file_available = True
        try:
            memory_dir = os.getenv("MEMORY_DIR", "memory")
            fm = MemoryFileManager(memory_dir)
            file_available = True
        except Exception:
            file_available = False
        
        # Check LLM availability for conversation analysis
        llm_available = bool(os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY'))
        
        return {
            "available_modes": {
                "database": {
                    "available": db_available,
                    "description": "PostgreSQL-based memory storage with vector search",
                    "features": ["vector_search", "complex_queries", "scalable"]
                },
                "file": {
                    "available": file_available,
                    "description": "File-based memory storage with markdown files",
                    "features": ["human_readable", "version_control", "portable", "6_memory_types"]
                }
            },
            "analysis_features": {
                "conversation_analysis": llm_available,
                "automatic_extraction": llm_available,
                "memory_types": ["profile", "event", "reminder", "important_event", "interests", "study"]
            },
            "recommended_mode": "file" if file_available else "database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Existing endpoints would continue here...
# ================================

# TODO: Include all the existing endpoints from the original main.py
# This is a simplified version showing the integration pattern


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 