"""
File Manager for Memory Operations

This module provides file-based memory management for character profiles and events.
Supports reading from and writing to profile.md and event.md files.
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
    
    Manages reading/writing of:
    - profile.md: Character profile information  
    - event.md: Character event records
    """
    
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
    
    def _get_memory_file_path(self, character_name: str, memory_type: str) -> Path:
        """Get memory file path for a character and memory type"""
        return self.memory_dir / f"{character_name.lower()}_{memory_type}.md"
    
    def read_profile(self, character_name: str) -> str:
        """
        Read character profile from profile.md file
        
        Args:
            character_name: Name of the character
            
        Returns:
            Profile content as string
        """
        try:
            file_path = self._get_memory_file_path(character_name, "profile")
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                logger.debug(f"Read profile for {character_name}: {len(content)} chars")
                return content
            else:
                logger.debug(f"No profile file found for {character_name}")
                return ""
        except Exception as e:
            logger.error(f"Error reading profile for {character_name}: {e}")
            return ""
    
    def write_profile(self, character_name: str, content: str) -> bool:
        """
        Write character profile to profile.md file
        
        Args:
            character_name: Name of the character
            content: Profile content to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_memory_file_path(character_name, "profile")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated profile for {character_name}: {len(content)} chars")
            return True
        except Exception as e:
            logger.error(f"Error writing profile for {character_name}: {e}")
            return False
    
    def read_events(self, character_name: str) -> str:
        """
        Read character events from event.md file
        
        Args:
            character_name: Name of the character
            
        Returns:
            Events content as string
        """
        try:
            file_path = self._get_memory_file_path(character_name, "event")
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                logger.debug(f"Read events for {character_name}: {len(content)} chars")
                return content
            else:
                logger.debug(f"No events file found for {character_name}")
                return ""
        except Exception as e:
            logger.error(f"Error reading events for {character_name}: {e}")
            return ""
    
    def write_events(self, character_name: str, content: str) -> bool:
        """
        Write character events to event.md file
        
        Args:
            character_name: Name of the character
            content: Events content to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_memory_file_path(character_name, "event")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated events for {character_name}: {len(content)} chars")
            return True
        except Exception as e:
            logger.error(f"Error writing events for {character_name}: {e}")
            return False
    
    def append_events(self, character_name: str, new_events: str) -> bool:
        """
        Append new events to existing event.md file
        
        Args:
            character_name: Name of the character
            new_events: New events content to append
            
        Returns:
            True if successful, False otherwise
        """
        try:
            existing_events = self.read_events(character_name)
            if existing_events.strip():
                combined_events = existing_events + "\n\n" + new_events
            else:
                combined_events = new_events
            
            return self.write_events(character_name, combined_events)
        except Exception as e:
            logger.error(f"Error appending events for {character_name}: {e}")
            return False
    
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
        
        for memory_type in ["profile", "event"]:
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
            profile_path = self._get_memory_file_path(character_name, "profile")
            event_path = self._get_memory_file_path(character_name, "event")
            
            info = {
                "character_name": character_name,
                "has_profile": profile_path.exists() and profile_path.stat().st_size > 0,
                "has_events": event_path.exists() and event_path.stat().st_size > 0,
                "profile_size": profile_path.stat().st_size if profile_path.exists() else 0,
                "events_size": event_path.stat().st_size if event_path.exists() else 0,
            }
            
            # Add modification times if files exist
            if profile_path.exists():
                info["profile_modified"] = datetime.fromtimestamp(profile_path.stat().st_mtime).isoformat()
            if event_path.exists():
                info["events_modified"] = datetime.fromtimestamp(event_path.stat().st_mtime).isoformat()
            
            return info
        except Exception as e:
            logger.error(f"Error getting info for {character_name}: {e}")
            return {
                "character_name": character_name,
                "has_profile": False,
                "has_events": False,
                "error": str(e)
            } 