"""
Activity type configuration file
Each md file type has its own folder and configuration
"""

from dataclasses import dataclass


@dataclass
class ActivityConfig:
    """Activity file configuration"""

    # Basic information
    name: str = "activity"
    filename: str = "activity.md"
    description: str = "Record all conversation and activity content"

    # Folder path
    folder_name: str = "activity"
    prompt_file: str = "prompt.txt"
    config_file: str = "config.py"

    # RAG configuration
    context: str = (
        "rag"  # "all" means put entire content in context, "rag" means use RAG search only
    )
    rag_length: int = 50  # RAG length, -1 means all, other values mean number of lines


# Create configuration instance
CONFIG = ActivityConfig()


def get_config():
    """Get activity configuration"""
    return CONFIG


def get_file_info():
    """Get file information"""
    return {
        "name": CONFIG.name,
        "filename": CONFIG.filename,
        "description": CONFIG.description,
        "folder": CONFIG.folder_name,
        "context": CONFIG.context,
        "rag_length": CONFIG.rag_length,
    }
