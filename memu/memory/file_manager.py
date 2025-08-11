"""
File-based Memory Management for MemU

Provides file operations for storing and retrieving character memory data
in markdown format.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..utils import get_logger

logger = get_logger(__name__)


class MemoryFileManager:
    """
    File-based memory manager for character profiles and memories.

    Manages memory storage in markdown files:
    - profile.md: Character profile information
    - events.md: Character event records
    - xxx.md: Other memory files
    """

    # Define basic categories and their file extensions
    BASIC_CATEGORIES = {
        "profile": ".md",
        "event": ".md"
    }

    def __init__(self, memory_dir: str = "memu/server/memory"):
        """
        Initialize File Manager

        Args:
            memory_dir: Directory to store memory files
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MemoryFileManager initialized with directory: {self.memory_dir}")

    def _get_memory_file_path(self, agent_id: str, user_id: str, category: str) -> Path:
        """
        Get the file path for a memory file with agent_id/user_id structure
        
        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Memory category
            
        Returns:
            Path: Full path to the memory file
        """
        extension = self.BASIC_CATEGORIES.get(category, ".md")
        filename = f"{category}{extension}"
        return self.memory_dir / agent_id / user_id / filename



    def read_memory_file(self, agent_id: str, user_id: str, category: str) -> str:
        """
        Read content from a memory file using agent_id/user_id structure

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category to read

        Returns:
            str: File content or empty string if not found
        """
        try:
            file_path = self._get_memory_file_path(agent_id, user_id, category)
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
            return ""
        except Exception as e:
            logger.error(f"Error reading {category} for agent {agent_id}, user {user_id}: {e}")
            return ""



    def write_memory_file(
        self, agent_id: str, user_id: str, category: str, content: str
    ) -> bool:
        """
        Write content to a memory file using agent_id/user_id structure

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category to write
            content: Content to write

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self._get_memory_file_path(agent_id, user_id, category)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            logger.debug(f"Written {category} for agent {agent_id}, user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error writing {category} for agent {agent_id}, user {user_id}: {e}")
            return False



    def append_memory_file(
        self, agent_id: str, user_id: str, category: str, content: str
    ) -> bool:
        """
        Append content to a memory file using agent_id/user_id structure

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category to append to
            content: Content to append

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            existing_content = self.read_memory_file(agent_id, user_id, category)
            if existing_content:
                new_content = existing_content + "\n\n" + content
            else:
                new_content = content
            return self.write_memory_file(agent_id, user_id, category, new_content)
        except Exception as e:
            logger.error(f"Error appending {category} for agent {agent_id}, user {user_id}: {e}")
            return False



    def delete_memory_file(self, agent_id: str, user_id: str, category: str) -> bool:
        """
        Delete a memory file using agent_id/user_id structure

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self._get_memory_file_path(agent_id, user_id, category)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted {category} for agent {agent_id}, user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {category} for agent {agent_id}, user {user_id}: {e}")
            return False



    def list_memory_files(self, agent_id: str, user_id: str) -> List[str]:
        """
        List all memory files for an agent-user pair

        Args:
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            List[str]: List of categories that exist for the agent-user pair
        """
        existing_categories = []
        for category in self.BASIC_CATEGORIES:
            file_path = self._get_memory_file_path(agent_id, user_id, category)
            if file_path.exists():
                existing_categories.append(category)
        return existing_categories



    def get_file_info(self, agent_id: str, user_id: str, category: str) -> Dict[str, Any]:
        """
        Get information about a memory file using agent_id/user_id structure

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category name

        Returns:
            Dict containing file information
        """
        file_path = self._get_memory_file_path(agent_id, user_id, category)

        if file_path.exists():
            stat = file_path.stat()
            content = self.read_memory_file(agent_id, user_id, category)
            return {
                "exists": True,
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content_length": len(content),
                "file_path": str(file_path),
                "agent_id": agent_id,
                "user_id": user_id,
            }
        else:
            return {
                "exists": False,
                "file_size": 0,
                "last_modified": None,
                "content_length": 0,
                "file_path": str(file_path),
                "agent_id": agent_id,
                "user_id": user_id,
            }
