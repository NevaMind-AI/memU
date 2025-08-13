"""Configuration module for MemU"""

# Import markdown configuration (primary public API)
from .markdown_config import (
    MarkdownConfigManager,
    MarkdownFileConfig,
    detect_file_type,
    get_all_file_configs,
    get_config_manager,
    get_optional_files,
    get_required_files,
    get_simple_summary,
)

__all__ = [
    # Markdown configuration
    "get_config_manager",
    "detect_file_type",
    "MarkdownConfigManager",
    "MarkdownFileConfig",
    # Simplified configuration API
    "get_required_files",
    "get_optional_files",
    "get_simple_summary",
    "get_all_file_configs",
]
