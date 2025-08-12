"""
File-based Memory Management for MemU

Provides file operations for storing and retrieving character memory data
in markdown format.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Set

from ..utils import get_logger
from ..config.markdown_config import get_config_manager

logger = get_logger(__name__)


class MemoryFileManager:
    """
    File-based memory manager for character profiles and memories.

    Manages memory storage in markdown files:
    - profile.md: Character profile information
    - events.md: Character event records
    - xxx.md: Other memory files
    """

    # Default file extension for all categories
    DEFAULT_EXTENSION = ".md"

    def __init__(self, memory_dir: str = "memu/server/memory", agent_id: str = None, user_id: str = None):
        """
        Initialize File Manager

        Args:
            memory_dir: Directory to store memory files
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir = self.memory_dir / "embeddings"
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        # Context for current agent/user (optional)
        self.agent_id = agent_id
        self.user_id = user_id

        self.config_manager = get_config_manager()

        # Maintain memory types by group
        self.memory_types: Dict[str, Dict[str, str]] = {"basic": {}, "cluster": {}}
        self._initialize_memory_types()

        logger.info(
            f"MemoryFileManager initialized with directory: {self.memory_dir}"
        )

    def _initialize_memory_types(self) -> None:
        """Load basic categories from MarkdownConfigManager into memory_types['basic']."""
        basic_map = self.config_manager.get_file_types_mapping()
        # Ensure a copy to avoid accidental external mutation
        self.memory_types["basic"] = dict(basic_map)
        cluster_set = self._get_cluster_categories(
            self.agent_id, self.user_id, set(self.memory_types["basic"].keys())
        )
        self.memory_types["cluster"] = cluster_set
        # Do not touch cluster here; it's context dependent

    # set_context removed: context is now provided at initialization time

    def get_flat_memory_types(self) -> Dict[str, str]:
        """Return a flattened mapping of all categories (basic + cluster) to filenames."""
        flat: Dict[str, str] = {}
        flat.update(self.memory_types.get("basic", {}))
        flat.update(self.memory_types.get("cluster", {}))
        return flat

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
        if category in self.memory_types["basic"]:
            filename = self.memory_types["basic"][category]
        elif category in self.memory_types["cluster"]:
            filename = self.memory_types["cluster"][category]
        else:
            filename = f"{category.replace(' ', '_')}{self.DEFAULT_EXTENSION}"
        return self.memory_dir / agent_id / user_id / filename


    def read_memory_file(self, category: str) -> str:
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
            file_path = self._get_memory_file_path(self.agent_id, self.user_id, category)
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
            return ""
        except Exception as e:
            logger.error(f"Error reading {category} for agent {self.agent_id}, user {self.user_id}: {e}")
            return ""


    def write_memory_file(
        self, category: str, content: str
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
            file_path = self._get_memory_file_path(self.agent_id, self.user_id, category)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            logger.debug(f"Written {category} for agent {self.agent_id}, user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error writing {category} for agent {self.agent_id}, user {self.user_id}: {e}")
            return False


    def append_memory_file(
        self, category: str, content: str
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
            existing_content = self.read_memory_file(category)
            if existing_content:
                new_content = existing_content + "\n" + content
            else:
                new_content = content
            return self.write_memory_file(category, new_content)
        except Exception as e:
            logger.error(f"Error appending {category} for agent {self.agent_id}, user {self.user_id}: {e}")
            return False



    def delete_memory_file(self, category: str) -> bool:
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
            file_path = self._get_memory_file_path(self.agent_id, self.user_id, category)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted {category} for agent {self.agent_id}, user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {category} for agent {self.agent_id}, user {self.user_id}: {e}")
            return False


    def list_memory_files(
        self,
        category_group: Literal["basic", "cluster", "all"] = "basic",
    ) -> List[str]:
        """
        List memory categories for an agent-user pair.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category_group: Which group to list: "basic", "cluster", or "all".

        Returns:
            List[str]: List of category names
        """
        basic_categories = self._get_basic_categories()
        cluster_categories = self._get_cluster_categories(self.agent_id, self.user_id, basic_categories).keys()

        if category_group == "basic":
            # Return all basic categories from config (not filtered by existence)
            return sorted(list(basic_categories))
        if category_group == "cluster":
            return sorted(list(cluster_categories))
        # all
        # all = all basic categories + cluster categories
        return sorted(list(basic_categories.union(cluster_categories)))


    def _get_basic_categories(self) -> Set[str]:
        """Get basic categories from MarkdownConfigManager."""
        return set(self.config_manager.get_all_file_types())

    def _get_cluster_categories(
        self, agent_id: str, user_id: str, basic_categories: Set[str]
    ) -> Dict[str, str]:
        """Scan existing files and derive cluster categories not in basic."""
        user_dir = self.memory_dir / agent_id / user_id
        if not user_dir.exists():
            return {}
        cluster: Dict[str, str] = {}
        for item in user_dir.glob(f"*{self.DEFAULT_EXTENSION}"):
            if item.is_file():
                category_name = item.stem
                if category_name not in basic_categories:
                    cluster[category_name.replace("_", " ")] = f"{category_name}{self.DEFAULT_EXTENSION}"
        return cluster

    def create_cluster_category(self, category: str) -> bool:
        """
        Create a new empty cluster category file if it does not exist.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: New cluster category name

        Returns:
            bool: True if created or already exists, False on error
        """
        try:
            _category = category.replace(" ", "_")
            file_path = self._get_memory_file_path(self.agent_id, self.user_id, _category)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_text("", encoding="utf-8")
            # Update in-memory cluster categories mapping
            self.memory_types.setdefault("cluster", {})[category] = f"{_category}{self.DEFAULT_EXTENSION}"
            return True
        except Exception as e:
            logger.error(
                f"Error creating cluster category {category} for agent {self.agent_id}, user {self.user_id}: {e}"
            )
            return False


    def get_char_embeddings_dir(self) -> Path:
        """
        Get the embeddings directory path for the current agent/user context
        
        Args:
            embeddings_base_dir: Base embeddings directory (usually memory_dir/embeddings)
            
        Returns:
            Path: Full path to the character's embeddings directory
        """
        if not self.agent_id or not self.user_id:
            raise ValueError("agent_id and user_id must be set to get embeddings directory")
        
        char_embeddings_dir = self.embeddings_dir / self.agent_id / self.user_id
        char_embeddings_dir.mkdir(parents=True, exist_ok=True)
        return char_embeddings_dir

    def get_file_info(self, category: str) -> Dict[str, Any]:
        """
        Get information about a memory file using agent_id/user_id structure

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category name

        Returns:
            Dict containing file information
        """
        file_path = self._get_memory_file_path(self.agent_id, self.user_id, category)

        if file_path.exists():
            stat = file_path.stat()
            content = self.read_memory_file(category)
            return {
                "exists": True,
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content_length": len(content),
                "file_path": str(file_path),
                "agent_id": self.agent_id,
                "user_id": self.user_id,
            }
        else:
            return {
                "exists": False,
                "file_size": 0,
                "last_modified": None,
                "content_length": 0,
                "file_path": str(file_path),
                "agent_id": self.agent_id,
                "user_id": self.user_id,
            }
