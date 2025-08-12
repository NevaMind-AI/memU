"""
Base Action Class for Memory Operations

Defines the interface and common functionality for all memory actions.
"""

import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Tuple

from ...utils import get_logger

logger = get_logger(__name__)


class BaseAction(ABC):
    """
    Base class for all memory actions

    Defines the standard interface that all actions must implement:
    - get_schema(): Return OpenAI-compatible function schema
    - execute(**kwargs): Execute the action with given arguments
    - validate_arguments(): Validate input arguments
    """

    def __init__(self, memory_core):
        """
        Initialize action with memory core

        Args:
            memory_core: Core memory functionality (file manager, embeddings, config, etc.)
        """
        self.memory_core = memory_core
        self.llm_client = memory_core.llm_client
        self.storage_manager = memory_core.storage_manager
        self.embedding_client = memory_core.embedding_client
        self.embeddings_enabled = memory_core.embeddings_enabled
        self.config_manager = memory_core.config_manager
        self.memory_types = memory_core.memory_types
        self.basic_memory_types = memory_core.memory_types["basic"]
        self.processing_order = memory_core.processing_order
        # self.embeddings_dir = memory_core.embeddings_dir

    @property
    @abstractmethod
    def action_name(self) -> str:
        """Return the name of this action"""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Return OpenAI-compatible function schema for this action

        Returns:
            Dict containing function schema with name, description, and parameters
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the action with provided arguments

        Args:
            **kwargs: Action-specific arguments

        Returns:
            Dict containing execution result with success status and data
        """
        pass

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input arguments against schema

        Args:
            arguments: Arguments to validate

        Returns:
            Dict with validation result
        """
        try:
            schema = self.get_schema()
            required_params = schema["parameters"].get("required", [])

            # Check for missing required parameters
            missing_params = [
                param for param in required_params if param not in arguments
            ]

            if missing_params:
                return {
                    "valid": False,
                    "error": f"Missing required parameters: {missing_params}",
                    "required_parameters": required_params,
                }

            return {
                "valid": True,
                "message": f"Validation passed for {self.action_name}",
            }

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _add_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Add standard metadata to action result"""
        if isinstance(result, dict):
            result["action_name"] = self.action_name
            result["timestamp"] = datetime.now().isoformat()
        return result

    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Standard error handling for actions"""
        error_result = {
            "success": False,
            "error": str(error),
            "action_name": self.action_name,
            "timestamp": datetime.now().isoformat(),
        }
        logger.error(f"Action {self.action_name} failed: {error}")
        return error_result

    # ================================
    # Memory ID Utilities
    # ================================

    def _generate_memory_id(self) -> str:
        short_uuid = str(uuid.uuid4())[:6]
        return f"{short_uuid}"

    def _add_memory_ids_to_content(self, content: str) -> str:
        """
        Add memory IDs to content lines

        Args:
            content: Raw content

        Returns:
            Content with memory IDs added to each line
        """
        if not content.strip():
            return content

        lines = content.split("\n")
        processed_lines = []

        for line in lines:
            line = line.strip()
            if line:  # Only process non-empty lines
                # Always remove existing memory ID and generate a new unique one
                if self._has_memory_id(line):
                    # Extract content without memory ID
                    _, clean_content = self._extract_memory_id(line)
                    line = clean_content

                # Generate new unique memory ID for this line
                memory_id = self._generate_memory_id()
                processed_lines.append(f"[{memory_id}] {line}")
            else:
                # Keep empty lines as is
                processed_lines.append("")

        return "\n".join(processed_lines)

    def _has_memory_id(self, line: str) -> bool:
        """
        Check if a line already has a memory ID

        Args:
            line: Line to check

        Returns:
            True if line starts with [memory_id] format
        """
        pattern = r"^\[[\w\d_]+\]\s+"
        return bool(re.match(pattern, line.strip()))

    def _extract_memory_id(self, line: str) -> Tuple[str, str]:
        """
        Extract memory ID and content from a line

        Args:
            line: Line with memory ID format: [memory_id] content

        Returns:
            Tuple of (memory_id, content)
        """
        line = line.strip()
        pattern = r"^\[([\w\d_]+)\]\s*(.*)"
        match = re.match(pattern, line)

        if match:
            memory_id = match.group(1)
            content = match.group(2)
            return memory_id, content
        else:
            # If no memory ID found, return empty ID and full line as content
            return "", line

    def _extract_content_without_ids(self, content: str) -> str:
        """
        Extract pure content without memory IDs for embedding generation

        Args:
            content: Content with memory IDs

        Returns:
            Content without memory IDs
        """
        if not content.strip():
            return content

        lines = content.split("\n")
        clean_lines = []

        for line in lines:
            if line.strip():
                _, clean_content = self._extract_memory_id(line)
                if clean_content:
                    clean_lines.append(clean_content)
            else:
                clean_lines.append("")

        return "\n".join(clean_lines)

    def _parse_memory_items(self, content: str) -> list[dict[str, Any]]:
        """
        Parse content into memory items with IDs, supporting both old and new timestamp formats

        Args:
            content: Content with memory IDs

        Returns:
            List of memory items with metadata
        """
        if not content.strip():
            return []

        lines = content.split("\n")
        items = []

        for i, line in enumerate(lines):
            line = line.strip()
            if line:  # Only process non-empty lines
                memory_id, mentioned_at, clean_content, links = (
                    self._extract_timestamped_memory_item(line)
                )

                if clean_content:
                    item = {
                        "memory_id": memory_id,
                        "mentioned_at": mentioned_at,
                        "content": clean_content,
                        "links": links,
                        "full_line": line,
                        "line_number": i + 1,
                    }
                    items.append(item)

        return items

    def _extract_timestamped_memory_item(self, line: str) -> Tuple[str, str, str, str]:
        """
        Extract memory ID, content, timestamp, and links from timestamped format
        Format: [memory_id][mentioned at date] content [links]

        Args:
            line: Line with timestamped memory format

        Returns:
            Tuple of (memory_id, content, mentioned_at, links)
        """
        import re

        line = line.strip()

        # Pattern to match: [memory_id][mentioned at date] content [links] (links optional)
        pattern = r"^\[([^\]]+)\]\[mentioned at ([^\]]+)\]\s*(.*?)(?:\s*\[([^\]]*)\])?$"
        match = re.match(pattern, line)

        if match:
            memory_id = match.group(1)
            mentioned_at = match.group(2)
            content = match.group(3).strip()
            links = match.group(4) if match.group(4) else ""
            return memory_id, mentioned_at, content, links
        else:
            return "", "", "", ""

    # ================================
    # Common utility methods that actions can use
    # ================================

    def _load_existing_memory(self, character_name: str) -> Dict[str, str]:
        """Load existing memory content for all categories"""
        existing_memory = {}

        for category in self.storage_manager.get_flat_memory_types():
            try:
                content = self._read_memory_content(character_name, category)
                existing_memory[category] = content if isinstance(content, str) else ""
            except Exception as e:
                logger.warning(
                    f"Failed to load existing {category} for {character_name}: {e}"
                )
                existing_memory[category] = ""

        return existing_memory

    def _read_memory_content(self, character_name: str, category: str) -> str:
        """Read memory content from storage"""
        try:
            # agent_id and user_id are managed inside storage_manager
            return self.storage_manager.read_memory_file(category)
        except Exception as e:
            logger.warning(f"Failed to read {category} for {character_name}: {e}")
            return ""

    def _save_memory_content(
        self, character_name: str, category: str, content: str
    ) -> bool:
        """Save memory content to storage"""
        try:
            # agent_id and user_id are managed inside storage_manager
            return self.storage_manager.write_memory_file(category, content)
        except Exception as e:
            logger.error(f"Failed to save {category} for {character_name}: {e}")
            return False

    def _append_memory_content(self, character_name: str, category: str, content: str) -> bool:
        """Append memory content to storage"""
        try:
            # agent_id and user_id are managed inside storage_manager
            return self.storage_manager.append_memory_file(category, content)
        except Exception as e:
            logger.error(f"Failed to append {category} for {character_name}: {e}")
            return False

    def _convert_conversation_to_text(self, conversation: list[dict]) -> str:
        """Convert conversation list to text format for LLM processing"""
        if not conversation or not isinstance(conversation, list):
            return ""

        text_parts = []
        for message in conversation:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            text_parts.append(f"{role.upper()}: {content}")

        return "\n".join(text_parts)
