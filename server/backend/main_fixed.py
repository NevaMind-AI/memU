"""
MemU Backend Management System - Fixed Version

Simplified API focused on file-based memory management with 6 memory types.
Removed dependencies on non-existent modules.
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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for MemU imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from memu.config import get_llm_config_manager
from memu.llm import OpenAIClient
from memu.memory.base import Memory
from memu.utils import get_logger

# Import the file-based memory API
from file_memory_api import file_memory_router

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MemU Backend Management System",
    description="File-based memory management with 6 memory types",
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

# ================================
# Basic Pydantic Models
# ================================

class SystemStats(BaseModel):
    file_memories: Dict[str, int] = {}
    llm_status: str = "unknown"
    memory_directory: str = ""

# ================================
# Basic System Stats
# ================================

def get_system_stats():
    """Get basic system statistics for file-based memory"""
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
        
        # Check LLM status
        llm_status = "available" if (os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY')) else "not_configured"
        
        stats = {
            "file_memories": {
                "total_characters": len(characters),
                "total_files": total_files,
                "total_size": total_size
            },
            "llm_status": llm_status,
            "memory_directory": memory_dir
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "file_memories": {"total_characters": 0, "total_files": 0, "total_size": 0},
            "llm_status": "error",
            "memory_directory": ""
        }

# ================================
# API routes
# ================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "message": "MemU Backend Management System API", 
        "status": "running",
        "version": "2.0.0",
        "features": ["file_memory", "conversation_analysis"]
    }

@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """Get system statistics"""
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
# Storage Mode Information
# ================================

@app.get("/api/storage/modes")
async def get_storage_modes():
    """Get available storage modes"""
    try:
        from memu import MemoryFileManager
        
        # Check file storage availability
        file_available = True
        try:
            memory_dir = os.getenv("MEMORY_DIR", "memory")
            fm = MemoryFileManager(memory_dir)
            file_available = True
        except Exception:
            file_available = False
        
        # Check LLM availability
        llm_available = bool(os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY'))
        
        return {
            "available_modes": {
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
            "recommended_mode": "file" if file_available else "none"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# Basic Conversation Storage (Simplified)
# ================================

class ConversationMessage(BaseModel):
    role: str
    content: str
    message_index: int

class SaveConversationRequest(BaseModel):
    agent_id: str
    user_id: str
    messages: List[ConversationMessage]
    session_id: Optional[str] = None

@app.post("/api/conversations/save")
async def save_conversation(request: SaveConversationRequest):
    """Save conversation to file (simplified version)"""
    try:
        # Create conversations directory if it doesn't exist
        conversations_dir = os.path.join(os.getenv("MEMORY_DIR", "memory"), "conversations")
        os.makedirs(conversations_dir, exist_ok=True)
        
        # Create conversation file
        timestamp = datetime.now().isoformat()
        filename = f"{request.agent_id}_{request.user_id}_{timestamp.replace(':', '-')}.json"
        filepath = os.path.join(conversations_dir, filename)
        
        conversation_data = {
            "agent_id": request.agent_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "created_at": timestamp,
            "messages": [msg.dict() for msg in request.messages]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved conversation to file: {filename}")
        
        return {
            "success": True, 
            "message": "Conversation saved successfully",
            "filename": filename,
            "created_at": timestamp,
            "message_count": len(request.messages)
        }
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        return {"success": False, "error": str(e)}

# ================================
# System Health Check
# ================================

@app.get("/api/health")
async def health_check():
    """Comprehensive health check"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Check file system
        try:
            from memu import MemoryFileManager
            memory_dir = os.getenv("MEMORY_DIR", "memory")
            fm = MemoryFileManager(memory_dir)
            characters = fm.list_characters()
            health_status["components"]["file_system"] = {
                "status": "healthy",
                "characters_count": len(characters),
                "memory_directory": memory_dir
            }
        except Exception as e:
            health_status["components"]["file_system"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check LLM availability
        llm_available = bool(os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY'))
        health_status["components"]["llm"] = {
            "status": "available" if llm_available else "not_configured",
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "azure_configured": bool(os.getenv('AZURE_OPENAI_API_KEY'))
        }
        
        return health_status
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 Starting MemU Backend Server (Fixed Version)...")
    print("📁 File-based Memory Management System")
    print("📍 API Interface: http://localhost:8000")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("📍 Health Check: http://localhost:8000/api/health")
    uvicorn.run(app, host="0.0.0.0", port=8000) 