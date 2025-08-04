"""
Event type configuration file
Record important events, activities, milestones, etc.
"""

from dataclasses import dataclass


@dataclass
class EventConfig:
    """Event file configuration"""

    # Basic information
    name: str = "event"
    filename: str = "event.md"
    description: str = "Record important events, activities and milestones"

    # Folder path
    folder_name: str = "event"
    prompt_file: str = "prompt.txt"
    config_file: str = "config.py"

    # RAG configuration
    context: str = (
        "rag"  # "all" means put entire content in context, "rag" means use RAG search only
    )
    rag_length: int = 30  # RAG length, -1 means all, other values mean number of lines


# Create configuration instance
CONFIG = EventConfig()


def get_config():
    """Get event configuration"""
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
