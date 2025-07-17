"""
File Manager for Memory Operations

This module provides file-based memory management for character profiles and events.
Supports reading from and writing to multiple memory file types:
- profile.md: Character profile information  
- event.md: Character event records
- reminder.md: Important reminders and todo items
- important_event.md: Significant life events and milestones
- interests.md: Hobbies, interests, and preferences
- study.md: Learning goals, courses, and educational content
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..utils import get_logger

logger = get_logger(__name__)


class MemoryFileManager:
    """
    File-based memory management for character profiles and events.
    
    Manages reading/writing of multiple memory file types:
    - profile.md: Character profile information  
    - event.md: Character event records
    - reminder.md: Important reminders and todo items
    - important_event.md: Significant life events and milestones
    - interests.md: Hobbies, interests, and preferences
    - study.md: Learning goals, courses, and educational content
    """
    
    # Define all supported memory types
    MEMORY_TYPES = [
        "profile",
        "event", 
        "reminder",
        "important_event",
        "interests",
        "study"
    ]
    
    def __init__(self, memory_dir: str = "memory"):
        """
        Initialize Memory File Manager
        
        Args:
            memory_dir: Directory to store memory files
        """
        self.memory_dir = Path(memory_dir)
        # Create memory directory if it doesn't exist
        self.memory_dir.mkdir(exist_ok=True)
        
        logger.info(f"MemoryFileManager initialized, memory directory: {self.memory_dir}")
        logger.info(f"Supported memory types: {', '.join(self.MEMORY_TYPES)}")
    
    def _get_memory_file_path(self, character_name: str, memory_type: str) -> Path:
        """Get memory file path for a character and memory type"""
        return self.memory_dir / f"{character_name.lower()}_{memory_type}.md"
    
    def _validate_memory_type(self, memory_type: str) -> bool:
        """Validate if memory type is supported"""
        return memory_type in self.MEMORY_TYPES
    
    def read_memory_file(self, character_name: str, memory_type: str) -> str:
        """
        Generic method to read any memory file type
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory file (profile, event, reminder, etc.)
            
        Returns:
            Memory content as string
        """
        if not self._validate_memory_type(memory_type):
            logger.error(f"Invalid memory type: {memory_type}. Supported types: {self.MEMORY_TYPES}")
            return ""
            
        try:
            file_path = self._get_memory_file_path(character_name, memory_type)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                logger.debug(f"Read {memory_type} for {character_name}: {len(content)} chars")
                return content
            else:
                logger.debug(f"No {memory_type} file found for {character_name}")
                return ""
        except Exception as e:
            logger.error(f"Error reading {memory_type} for {character_name}: {e}")
            return ""

    def write_memory_file(self, character_name: str, memory_type: str, content: str) -> bool:
        """
        Generic method to write any memory file type
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory file (profile, event, reminder, etc.)
            content: Content to write
            
        Returns:
            True if successful, False otherwise
        """
        if not self._validate_memory_type(memory_type):
            logger.error(f"Invalid memory type: {memory_type}. Supported types: {self.MEMORY_TYPES}")
            return False
            
        try:
            file_path = self._get_memory_file_path(character_name, memory_type)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated {memory_type} for {character_name}: {len(content)} chars")
            return True
        except Exception as e:
            logger.error(f"Error writing {memory_type} for {character_name}: {e}")
            return False

    def append_memory_file(self, character_name: str, memory_type: str, new_content: str) -> bool:
        """
        Generic method to append content to any memory file type
        
        Args:
            character_name: Name of the character
            memory_type: Type of memory file (profile, event, reminder, etc.)
            new_content: New content to append
            
        Returns:
            True if successful, False otherwise
        """
        if not self._validate_memory_type(memory_type):
            logger.error(f"Invalid memory type: {memory_type}. Supported types: {self.MEMORY_TYPES}")
            return False
            
        try:
            existing_content = self.read_memory_file(character_name, memory_type)
            if existing_content.strip():
                combined_content = existing_content + "\n\n" + new_content
            else:
                combined_content = new_content
            
            return self.write_memory_file(character_name, memory_type, combined_content)
        except Exception as e:
            logger.error(f"Error appending {memory_type} for {character_name}: {e}")
            return False

    # Legacy methods for backward compatibility
    def read_profile(self, character_name: str) -> str:
        """Read character profile from profile.md file"""
        return self.read_memory_file(character_name, "profile")

    def write_profile(self, character_name: str, content: str) -> bool:
        """Write character profile to profile.md file"""
        return self.write_memory_file(character_name, "profile", content)

    def read_events(self, character_name: str) -> str:
        """Read character events from event.md file"""
        return self.read_memory_file(character_name, "event")

    def write_events(self, character_name: str, content: str) -> bool:
        """Write character events to event.md file"""
        return self.write_memory_file(character_name, "event", content)

    def append_events(self, character_name: str, new_events: str) -> bool:
        """Append new events to existing event.md file"""
        return self.append_memory_file(character_name, "event", new_events)

    # New methods for additional memory types
    def read_reminders(self, character_name: str) -> str:
        """Read character reminders from reminder.md file"""
        return self.read_memory_file(character_name, "reminder")

    def write_reminders(self, character_name: str, content: str) -> bool:
        """Write character reminders to reminder.md file"""
        return self.write_memory_file(character_name, "reminder", content)

    def append_reminders(self, character_name: str, new_reminders: str) -> bool:
        """Append new reminders to existing reminder.md file"""
        return self.append_memory_file(character_name, "reminder", new_reminders)

    def read_important_events(self, character_name: str) -> str:
        """Read character important events from important_event.md file"""
        return self.read_memory_file(character_name, "important_event")

    def write_important_events(self, character_name: str, content: str) -> bool:
        """Write character important events to important_event.md file"""
        return self.write_memory_file(character_name, "important_event", content)

    def append_important_events(self, character_name: str, new_events: str) -> bool:
        """Append new important events to existing important_event.md file"""
        return self.append_memory_file(character_name, "important_event", new_events)

    def read_interests(self, character_name: str) -> str:
        """Read character interests from interests.md file"""
        return self.read_memory_file(character_name, "interests")

    def write_interests(self, character_name: str, content: str) -> bool:
        """Write character interests to interests.md file"""
        return self.write_memory_file(character_name, "interests", content)

    def append_interests(self, character_name: str, new_interests: str) -> bool:
        """Append new interests to existing interests.md file"""
        return self.append_memory_file(character_name, "interests", new_interests)

    def read_study(self, character_name: str) -> str:
        """Read character study information from study.md file"""
        return self.read_memory_file(character_name, "study")

    def write_study(self, character_name: str, content: str) -> bool:
        """Write character study information to study.md file"""
        return self.write_memory_file(character_name, "study", content)

    def append_study(self, character_name: str, new_study: str) -> bool:
        """Append new study information to existing study.md file"""
        return self.append_memory_file(character_name, "study", new_study)

    def list_characters(self) -> List[str]:
        """
        List all characters that have memory files
        
        Returns:
            List of character names
        """
        try:
            characters = set()
            for file_path in self.memory_dir.glob("*_*.md"):
                if file_path.is_file() and file_path.stat().st_size > 0:
                    filename = file_path.stem
                    if "_" in filename:
                        character_name = filename.rsplit("_", 1)[0]
                        characters.add(character_name)
            
            result = sorted(list(characters))
            logger.debug(f"Found {len(result)} characters with memory files")
            return result
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            return []
    
    def clear_character_memory(self, character_name: str) -> Dict[str, bool]:
        """
        Clear all memory files for a character
        
        Args:
            character_name: Name of the character
            
        Returns:
            Dict with success status for each file type
        """
        results = {}
        
        for memory_type in self.MEMORY_TYPES:
            try:
                file_path = self._get_memory_file_path(character_name, memory_type)
                if file_path.exists():
                    file_path.unlink()
                    results[memory_type] = True
                    logger.info(f"Cleared {memory_type} for {character_name}")
                else:
                    results[memory_type] = True  # Nothing to clear
                    logger.debug(f"No {memory_type} file to clear for {character_name}")
            except Exception as e:
                logger.error(f"Error clearing {memory_type} for {character_name}: {e}")
                results[memory_type] = False
        
        return results
    
    def get_character_info(self, character_name: str) -> Dict[str, Any]:
        """
        Get information about a character's memory files
        
        Args:
            character_name: Name of the character
            
        Returns:
            Dict with character information
        """
        try:
            info = {
                "character_name": character_name,
            }
            
            # Check each memory type
            for memory_type in self.MEMORY_TYPES:
                file_path = self._get_memory_file_path(character_name, memory_type)
                has_file = file_path.exists() and file_path.stat().st_size > 0
                file_size = file_path.stat().st_size if file_path.exists() else 0
                
                info[f"has_{memory_type}"] = has_file
                info[f"{memory_type}_size"] = file_size
                
                # Add modification time if file exists
                if file_path.exists():
                    info[f"{memory_type}_modified"] = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            return info
        except Exception as e:
            logger.error(f"Error getting info for {character_name}: {e}")
            error_info = {
                "character_name": character_name,
                "error": str(e)
            }
            # Add default values for all memory types
            for memory_type in self.MEMORY_TYPES:
                error_info[f"has_{memory_type}"] = False
                error_info[f"{memory_type}_size"] = 0
            return error_info

    def get_all_memory_content(self, character_name: str) -> Dict[str, str]:
        """
        Get all memory content for a character
        
        Args:
            character_name: Name of the character
            
        Returns:
            Dict with all memory content by type
        """
        content = {}
        for memory_type in self.MEMORY_TYPES:
            content[memory_type] = self.read_memory_file(character_name, memory_type)
        return content 