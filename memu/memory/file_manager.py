"""
File-based Memory Management for MemU

Provides file operations for storing and retrieving character memory data
in markdown format.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..utils import get_logger

logger = get_logger(__name__)


class MemoryFileManager:
    """
    File-based memory manager for character profiles and memories.
    
    Manages memory storage in markdown files:
    - profile.md: Character profile information
    - events.md: Character event records  
    - reminders.md: Important reminders and todo items
    - interests.md: Hobbies, interests, and preferences
    - study.md: Learning goals, courses, and educational content
    - activity.md: Activity summaries from conversations
    """
    
    # Define supported memory types and their file extensions
    MEMORY_TYPES = {
        "profile": ".md",
        "event": ".md", 
        "reminder": ".md",
        "interests": ".md",
        "study": ".md",
        "activity": ".md"
    }
    
    def __init__(self, memory_dir: str = "memory"):
        """
        Initialize File Manager
        
        Args:
            memory_dir: Directory to store memory files
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MemoryFileManager initialized with directory: {self.memory_dir}")
    
    def _get_memory_file_path(self, character_name: str, memory_type: str) -> Path:
        """Get the file path for a character's memory file"""
        extension = self.MEMORY_TYPES.get(memory_type, ".md")
        filename = f"{character_name}_{memory_type}{extension}"
        return self.memory_dir / filename
    
    def read_memory_file(self, character_name: str, memory_type: str) -> str:
        """
        Read content from a character's memory file
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory to read
            
        Returns:
            str: File content or empty string if not found
        """
        try:
            file_path = self._get_memory_file_path(character_name, memory_type)
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
            return ""
        except Exception as e:
            logger.error(f"Error reading {memory_type} for {character_name}: {e}")
            return ""
    
    def write_memory_file(self, character_name: str, memory_type: str, content: str) -> bool:
        """
        Write content to a character's memory file
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory to write
            content: Content to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self._get_memory_file_path(character_name, memory_type)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            logger.debug(f"Written {memory_type} for {character_name}")
            return True
        except Exception as e:
            logger.error(f"Error writing {memory_type} for {character_name}: {e}")
            return False
    
    def append_memory_file(self, character_name: str, memory_type: str, content: str) -> bool:
        """
        Append content to a character's memory file
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory to append to
            content: Content to append
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            existing_content = self.read_memory_file(character_name, memory_type)
            if existing_content:
                new_content = existing_content + "\n\n" + content
            else:
                new_content = content
            return self.write_memory_file(character_name, memory_type, new_content)
        except Exception as e:
            logger.error(f"Error appending {memory_type} for {character_name}: {e}")
            return False
    
    def delete_memory_file(self, character_name: str, memory_type: str) -> bool:
        """
        Delete a character's memory file
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self._get_memory_file_path(character_name, memory_type)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted {memory_type} for {character_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {memory_type} for {character_name}: {e}")
            return False
    
    def list_character_files(self, character_name: str) -> List[str]:
        """
        List all memory files for a character
        
        Args:
            character_name: Name of the character
            
        Returns:
            List[str]: List of memory types that exist for the character
        """
        existing_types = []
        for memory_type in self.MEMORY_TYPES:
            file_path = self._get_memory_file_path(character_name, memory_type)
            if file_path.exists():
                existing_types.append(memory_type)
        return existing_types
    
    def get_file_info(self, character_name: str, memory_type: str) -> Dict[str, Any]:
        """
        Get information about a memory file
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory
            
        Returns:
            Dict containing file information
        """
        file_path = self._get_memory_file_path(character_name, memory_type)
        
        if file_path.exists():
            stat = file_path.stat()
            content = self.read_memory_file(character_name, memory_type)
            return {
                "exists": True,
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content_length": len(content),
                "file_path": str(file_path)
            }
        else:
            return {
                "exists": False,
                "file_size": 0,
                "last_modified": None,
                "content_length": 0,
                "file_path": str(file_path)
            }
    
    # Legacy method aliases for backward compatibility
    def read_profile(self, character_name: str) -> str:
        """Read character profile"""
        return self.read_memory_file(character_name, "profile")
    
    def write_profile(self, character_name: str, content: str) -> bool:
        """Write character profile"""
        return self.write_memory_file(character_name, "profile", content)
    
    def read_events(self, character_name: str) -> str:
        """Read character events"""
        return self.read_memory_file(character_name, "event")
    
    def write_events(self, character_name: str, content: str) -> bool:
        """Write character events"""
        return self.write_memory_file(character_name, "event", content)
    
    def read_reminders(self, character_name: str) -> str:
        """Read character reminders"""
        return self.read_memory_file(character_name, "reminder")
    
    def write_reminders(self, character_name: str, content: str) -> bool:
        """Write character reminders"""
        return self.write_memory_file(character_name, "reminder", content)
    
    def read_interests(self, character_name: str) -> str:
        """Read character interests"""
        return self.read_memory_file(character_name, "interests")
    
    def write_interests(self, character_name: str, content: str) -> bool:
        """Write character interests"""
        return self.write_memory_file(character_name, "interests", content)
    
    def read_study(self, character_name: str) -> str:
        """Read character study information"""
        return self.read_memory_file(character_name, "study")
    
    def write_study(self, character_name: str, content: str) -> bool:
        """Write character study information"""
        return self.write_memory_file(character_name, "study", content)
    
    def read_activity(self, character_name: str) -> str:
        """Read character activity summary"""
        return self.read_memory_file(character_name, "activity")
    
    def write_activity(self, character_name: str, content: str) -> bool:
        """Write character activity summary"""
        return self.write_memory_file(character_name, "activity", content)
    
    # Additional legacy aliases for compatibility
    def read_important_events(self, character_name: str) -> str:
        """Read important events (alias for events)"""
        return self.read_events(character_name)
    
    def write_important_events(self, character_name: str, content: str) -> bool:
        """Write important events (alias for events)"""
        return self.write_events(character_name, content) 