"""
MemU Markdown Configuration System - YAML based configuration

All file type configurations are centralized in a single YAML file to make
maintenance and debugging easier. Each item also points to its prompt file
under its corresponding folder when available.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class MarkdownFileConfig:
    """Minimal markdown file configuration"""

    name: str  # File type name
    filename: str  # Filename
    description: str  # File description
    folder_path: str  # Folder path
    prompt_path: str  # Prompt file path
    context: str = (
        "rag"  # Context mode: "all" means put entire content in context, "rag" means use RAG search
    )
    rag_length: int = 50  # RAG length, -1 means all, other values mean number of lines


class MarkdownConfigManager:
    """Manager for loading markdown file configurations from YAML."""

    def __init__(self):
        self.config_base_dir = Path(__file__).parent
        self.yaml_path = self.config_base_dir / "memory_cat_config.yaml"
        self._files_config: Dict[str, MarkdownFileConfig] = {}
        self._processing_order: List[str] = []
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """Load all configurations from YAML file.

        Supports the following YAML structure:

        categories:
          system: [ {name, filename, description, folder_name, prompt_file, context, rag_length}, ... ]
          custom: [ ... ]

        Both system and custom lists are concatenated to form the basic categories.
        """
        self._files_config = {}

        if not self.yaml_path.exists():
            print(f"Warning: YAML configuration file not found: {self.yaml_path}")
            self._processing_order = []
            return

        try:
            raw_config: Dict[str, Any] = yaml.safe_load(
                self.yaml_path.read_text(encoding="utf-8")
            ) or {}
        except Exception as e:
            print(f"Warning: Failed to parse YAML configuration {self.yaml_path}: {e}")
            self._processing_order = []
            return

        categories_section: Dict[str, Any] = raw_config.get("categories", {}) or {}
        system_list = categories_section.get("system", []) or []
        custom_list = categories_section.get("custom", []) or []

        # Maintain order: system first, then custom
        combined_items: List[Dict[str, Any]] = []
        if isinstance(system_list, list):
            combined_items.extend(system_list)
        if isinstance(custom_list, list):
            combined_items.extend(custom_list)

        processing_order: List[str] = []

        for item in combined_items:
            if not isinstance(item, dict):
                continue
            name: Optional[str] = item.get("name")
            if not name:
                # Skip invalid entries without name
                continue

            # Compute folder and prompt paths
            folder_name: str = item.get("folder_name", name)
            folder_path = self.config_base_dir / folder_name
            prompt_file_name: str = item.get("prompt_file", "prompt.txt")
            prompt_path = folder_path / prompt_file_name

            self._files_config[name] = MarkdownFileConfig(
                name=name,
                filename=item.get("filename", f"{name}.md"),
                description=item.get("description", ""),
                folder_path=str(folder_path),
                prompt_path=str(prompt_path) if prompt_path.exists() else "",
                context=item.get("context", "rag"),
                rag_length=int(item.get("rag_length", 50)),
            )
            processing_order.append(name)

        self._processing_order = processing_order

    def get_file_config(self, file_type: str) -> Optional[MarkdownFileConfig]:
        """Get configuration for specified file type"""
        return self._files_config.get(file_type)

    def get_all_file_types(self) -> List[str]:
        """Get all supported file types"""
        return list(self._files_config.keys())

    def get_processing_order(self) -> List[str]:
        """Get processing order"""
        return self._processing_order.copy()

    def get_file_description(self, file_type: str) -> str:
        """Get description of file type"""
        config = self.get_file_config(file_type)
        return config.description if config else ""

    def validate_file_type(self, file_type: str) -> bool:
        """Validate if file type is supported"""
        return file_type in self._files_config

    def get_prompt_path(self, file_type: str) -> str:
        """Get prompt file path"""
        config = self.get_file_config(file_type)
        return config.prompt_path if config else ""

    def get_folder_path(self, file_type: str) -> str:
        """Get folder path"""
        config = self.get_file_config(file_type)
        return config.folder_path if config else ""

    def get_file_types_mapping(self) -> Dict[str, str]:
        """Get mapping from file type to filename"""
        return {name: config.filename for name, config in self._files_config.items()}

    def get_context_mode(self, file_type: str) -> str:
        """Get context mode for specified file type"""
        config = self.get_file_config(file_type)
        return config.context if config else "rag"

    def get_rag_length(self, file_type: str) -> int:
        """Get RAG length for specified file type"""
        config = self.get_file_config(file_type)
        return config.rag_length if config else 50

    def get_all_context_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get context configurations for all file types"""
        return {
            file_type: {"context": config.context, "rag_length": config.rag_length}
            for file_type, config in self._files_config.items()
        }


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> MarkdownConfigManager:
    """Get configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MarkdownConfigManager()
    return _config_manager


# Maintain backward compatible API functions


def detect_file_type(filename: str, content: str = "") -> str:
    """Intelligently detect file type based on filename"""
    manager = get_config_manager()
    file_types = manager.get_all_file_types()

    if not file_types:
        return "activity"

    # Detect based on filename keywords
    filename_lower = filename.lower()

    # Detect profile type
    if any(
        keyword in filename_lower
        for keyword in ["profile", "personal_info", "bio", "resume"]
    ):
        if "profile" in file_types:
            return "profile"

    # Detect event type
    if any(
        keyword in filename_lower
        for keyword in ["event", "events", "activity", "milestone"]
    ):
        if "event" in file_types:
            return "event"

    # Detect activity type
    if any(
        keyword in filename_lower
        for keyword in ["activity", "activities", "daily", "diary", "log"]
    ):
        if "activity" in file_types:
            return "activity"

    # If no match, return first available type
    return file_types[0]


def get_required_files() -> List[str]:
    """Get list of required file types"""
    manager = get_config_manager()
    return manager.get_all_file_types()


def get_optional_files() -> List[str]:
    """Get list of optional file types (currently empty)"""
    return []


def get_simple_summary() -> Dict[str, Any]:
    """Get configuration summary"""
    manager = get_config_manager()
    file_types = manager.get_all_file_types()

    required_files = {}
    for file_type in file_types:
        config = manager.get_file_config(file_type)
        if config:
            required_files[file_type] = {
                "filename": config.filename,
                "description": config.description,
                "folder": config.folder_path,
                "context": config.context,
                "rag_length": config.rag_length,
            }

    return {
        "required_files": required_files,
        "optional_files": {},
        "total_files": len(file_types),
        "processing_principle": f"Load {len(file_types)} categories from YAML (system + custom)",
    }


def get_all_file_configs() -> Dict[str, MarkdownFileConfig]:
    """Get all file configurations"""
    manager = get_config_manager()
    return {
        file_type: manager.get_file_config(file_type)
        for file_type in manager.get_all_file_types()
    }
