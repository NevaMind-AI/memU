"""
Profile type configuration file
Record character's basic personal information only (age, location, background, etc.) - NO EVENTS
"""

from dataclasses import dataclass


@dataclass
class ProfileConfig:
    """Profile file configuration"""

    # Basic information
    name: str = "profile"
    filename: str = "profile.md"
    description: str = (
        "Record character's basic personal information only (age, location, background, demographics) - excludes events and activities"
    )

    # Folder path
    folder_name: str = "profile"
    prompt_file: str = "prompt.txt"
    config_file: str = "config.py"

    # RAG configuration
    context: str = (
        "all"  # "all" means put entire content in context, "rag" means use RAG search only
    )
    rag_length: int = -1  # RAG length, -1 means all, other values mean number of lines


# Create configuration instance
CONFIG = ProfileConfig()


def get_config():
    """Get profile configuration"""
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
