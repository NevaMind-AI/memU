"""
File-based Memory API Module for MemU Backend

Provides API endpoints for file-based memory management with support for 6 memory types:
- profile.md: Character profile information
- event.md: Character event records
- reminder.md: Important reminders and todo items
- important_event.md: Significant life events and milestones
- interests.md: Hobbies, interests, and preferences
- study.md: Learning goals, courses, and educational content
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import MemU components
from memu import MemoryFileManager
try:
    from memu import MemoryAgent
    MEMORY_AGENT_AVAILABLE = True
except ImportError:
    MEMORY_AGENT_AVAILABLE = False
    
from memu.llm import OpenAIClient
try:
    from memu.llm import AzureOpenAIClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


# ================================
# Pydantic Models
# ================================

class MemoryFileInfo(BaseModel):
    character_name: str
    memory_type: str
    has_content: bool
    file_size: int
    last_modified: Optional[str] = None
    content_preview: Optional[str] = None


class MemoryFileContent(BaseModel):
    character_name: str
    memory_type: str
    content: str
    file_size: int
    last_modified: str


class UpdateMemoryFileRequest(BaseModel):
    character_name: str
    memory_type: str
    content: str
    append: bool = False


class ConversationAnalysisRequest(BaseModel):
    character_name: str
    conversation: str
    session_date: Optional[str] = None


class ConversationAnalysisResponse(BaseModel):
    success: bool
    character_name: str
    session_date: Optional[str]
    update_results: Dict[str, bool]
    files_updated: Dict[str, bool]
    new_content: Dict[str, str]
    error: Optional[str] = None


class CharacterSummary(BaseModel):
    character_name: str
    total_files: int
    file_details: Dict[str, MemoryFileInfo]
    total_size: int
    last_activity: Optional[str]


class BulkOperationRequest(BaseModel):
    character_names: List[str]
    operation: str  # "clear_all", "export_all", "backup_all"


# ================================
# Initialize Router
# ================================

router = APIRouter(prefix="/api/file-memory", tags=["File Memory"])

# Global variables for memory management
file_manager = None
memory_agent = None


def get_file_manager() -> MemoryFileManager:
    """Get or create file manager instance"""
    global file_manager
    if file_manager is None:
        memory_dir = os.getenv("MEMORY_DIR", "memory")
        file_manager = MemoryFileManager(memory_dir)
    return file_manager


def get_memory_agent() -> Optional[Any]:
    """Get or create memory agent with LLM client"""
    global memory_agent
    if memory_agent is None and MEMORY_AGENT_AVAILABLE:
        try:
            # Try to initialize LLM client
            if os.getenv('AZURE_OPENAI_API_KEY') and AZURE_AVAILABLE:
                llm_client = AzureOpenAIClient()
            elif os.getenv('OPENAI_API_KEY'):
                llm_client = OpenAIClient()
            else:
                return None
            
            memory_dir = os.getenv("MEMORY_DIR", "memory")
            memory_agent = MemoryAgent(
                llm_client=llm_client,
                memory_dir=memory_dir,
                use_database=False
            )
        except Exception as e:
            print(f"Error initializing memory agent: {e}")
            return None
    
    return memory_agent


# ================================
# Character Management Endpoints
# ================================

@router.get("/characters", response_model=List[str])
async def list_characters():
    """Get list of all characters with memory files"""
    try:
        fm = get_file_manager()
        characters = fm.list_characters()
        return characters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters/{character_name}/summary", response_model=CharacterSummary)
async def get_character_summary(character_name: str):
    """Get comprehensive summary of a character's memory files"""
    try:
        fm = get_file_manager()
        char_info = fm.get_character_info(character_name)
        
        # Build file details
        file_details = {}
        total_size = 0
        last_activity = None
        
        for memory_type in fm.MEMORY_TYPES:
            has_file = char_info.get(f"has_{memory_type}", False)
            file_size = char_info.get(f"{memory_type}_size", 0)
            modified_time = char_info.get(f"{memory_type}_modified", None)
            
            # Get content preview
            content_preview = None
            if has_file:
                content = fm.read_memory_file(character_name, memory_type)
                content_preview = content[:200] + "..." if len(content) > 200 else content
            
            file_details[memory_type] = MemoryFileInfo(
                character_name=character_name,
                memory_type=memory_type,
                has_content=has_file,
                file_size=file_size,
                last_modified=modified_time,
                content_preview=content_preview
            )
            
            total_size += file_size
            
            # Track latest activity
            if modified_time and (not last_activity or modified_time > last_activity):
                last_activity = modified_time
        
        return CharacterSummary(
            character_name=character_name,
            total_files=len([f for f in file_details.values() if f.has_content]),
            file_details=file_details,
            total_size=total_size,
            last_activity=last_activity
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/characters/{character_name}")
async def clear_character_memory(character_name: str):
    """Clear all memory files for a character"""
    try:
        fm = get_file_manager()
        results = fm.clear_character_memory(character_name)
        
        return {
            "success": all(results.values()),
            "character_name": character_name,
            "cleared_files": results,
            "message": f"Cleared memory files for {character_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Memory File Operations
# ================================

@router.get("/characters/{character_name}/files/{memory_type}", response_model=MemoryFileContent)
async def get_memory_file(character_name: str, memory_type: str):
    """Get content of a specific memory file"""
    try:
        fm = get_file_manager()
        
        if memory_type not in fm.MEMORY_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid memory type. Supported types: {fm.MEMORY_TYPES}"
            )
        
        content = fm.read_memory_file(character_name, memory_type)
        file_path = fm._get_memory_file_path(character_name, memory_type)
        
        file_size = file_path.stat().st_size if file_path.exists() else 0
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else datetime.now().isoformat()
        
        return MemoryFileContent(
            character_name=character_name,
            memory_type=memory_type,
            content=content,
            file_size=file_size,
            last_modified=last_modified
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/characters/{character_name}/files/{memory_type}")
async def update_memory_file(character_name: str, memory_type: str, request: UpdateMemoryFileRequest):
    """Update content of a specific memory file"""
    try:
        fm = get_file_manager()
        
        if memory_type not in fm.MEMORY_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid memory type. Supported types: {fm.MEMORY_TYPES}"
            )
        
        if request.append:
            success = fm.append_memory_file(character_name, memory_type, request.content)
        else:
            success = fm.write_memory_file(character_name, memory_type, request.content)
        
        if success:
            return {
                "success": True,
                "character_name": character_name,
                "memory_type": memory_type,
                "operation": "append" if request.append else "write",
                "content_length": len(request.content),
                "message": f"Updated {memory_type} for {character_name}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update memory file")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters/{character_name}/files/{memory_type}/download")
async def download_memory_file(character_name: str, memory_type: str):
    """Download a memory file"""
    try:
        fm = get_file_manager()
        
        if memory_type not in fm.MEMORY_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid memory type. Supported types: {fm.MEMORY_TYPES}"
            )
        
        file_path = fm._get_memory_file_path(character_name, memory_type)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Memory file not found")
        
        return FileResponse(
            path=str(file_path),
            filename=f"{character_name}_{memory_type}.md",
            media_type="text/markdown"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Conversation Analysis
# ================================

@router.post("/analyze-conversation", response_model=ConversationAnalysisResponse)
async def analyze_conversation(request: ConversationAnalysisRequest):
    """Analyze conversation and update all memory file types"""
    try:
        if not MEMORY_AGENT_AVAILABLE:
            raise HTTPException(
                status_code=503, 
                detail="Memory agent not available. Please check MemoryAgent installation."
            )
            
        agent = get_memory_agent()
        
        if not agent:
            raise HTTPException(
                status_code=503, 
                detail="LLM client not available. Please configure OPENAI_API_KEY or AZURE_OPENAI_API_KEY"
            )
        
        # Analyze conversation and update memory
        result = agent.update_character_memory(
            character_name=request.character_name,
            conversation=request.conversation,
            session_date=request.session_date or datetime.now().strftime("%Y-%m-%d")
        )
        
        if result["success"]:
            return ConversationAnalysisResponse(
                success=True,
                character_name=request.character_name,
                session_date=request.session_date,
                update_results=result.get("update_results", {}),
                files_updated={
                    "profile": result.get("profile_updated", False),
                    "events": result.get("events_updated", False),
                    "reminders": result.get("reminders_updated", False),
                    "important_events": result.get("important_events_updated", False),
                    "interests": result.get("interests_updated", False),
                    "study": result.get("study_updated", False)
                },
                new_content=result.get("new_content", {})
            )
        else:
            return ConversationAnalysisResponse(
                success=False,
                character_name=request.character_name,
                session_date=request.session_date,
                update_results={},
                files_updated={},
                new_content={},
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Bulk Operations
# ================================

@router.post("/bulk-operations")
async def perform_bulk_operation(request: BulkOperationRequest):
    """Perform bulk operations on multiple characters"""
    try:
        fm = get_file_manager()
        results = {}
        
        for character_name in request.character_names:
            try:
                if request.operation == "clear_all":
                    result = fm.clear_character_memory(character_name)
                    results[character_name] = {"success": all(result.values()), "details": result}
                elif request.operation == "export_all":
                    content = fm.get_all_memory_content(character_name)
                    results[character_name] = {"success": True, "content": content}
                else:
                    results[character_name] = {"success": False, "error": f"Unknown operation: {request.operation}"}
            except Exception as e:
                results[character_name] = {"success": False, "error": str(e)}
        
        return {
            "operation": request.operation,
            "processed_characters": len(request.character_names),
            "results": results,
            "overall_success": all(r.get("success", False) for r in results.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# System Information
# ================================

@router.get("/system/info")
async def get_system_info():
    """Get file-based memory system information"""
    try:
        fm = get_file_manager()
        agent = get_memory_agent()
        
        characters = fm.list_characters()
        
        # Calculate total statistics
        total_files = 0
        total_size = 0
        
        for character in characters:
            char_info = fm.get_character_info(character)
            for memory_type in fm.MEMORY_TYPES:
                if char_info.get(f"has_{memory_type}", False):
                    total_files += 1
                    total_size += char_info.get(f"{memory_type}_size", 0)
        
        return {
            "memory_directory": str(fm.memory_dir),
            "supported_file_types": fm.MEMORY_TYPES,
            "total_characters": len(characters),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "llm_available": agent is not None,
            "analysis_enabled": agent is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export router
file_memory_router = router 