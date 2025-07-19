"""
MemU Memory Module - Clean Modular Architecture

Modern memory system with specialized independent agents:

CORE ARCHITECTURE:
- BaseAgent: Abstract base class for all specialized agents
- Specialized Agents: ActivityAgent, ProfileAgent, EventAgent, ReminderAgent, InterestAgent, StudyAgent
- MetaAgent: Coordinator for orchestrating specialized agents

STORAGE SUPPORT:
- MemoryFileManager: File operations for memory storage (.md files)
- MemoryDatabaseManager: Database operations with PostgreSQL + pgvector
- EmbeddingClient: Vector embedding generation for semantic search

ARCHITECTURE FLOW:
1. Raw Conversation → ActivityAgent → activity.md
2. activity.md → Specialized Agents (parallel) → memory files
3. All agents have complete independence with their own LLM processing and storage

BENEFITS:
- True modularity: Each agent is independent and complete
- Easy extension: Add new agent types without changing existing code
- Better performance: Agents can run in parallel
- Clean separation: Each agent handles one memory type
- No legacy code: Simple, focused architecture
"""

# Core Memory classes
from .base import Memory, ProfileMemory, EventMemory
from .meta_agent import MetaAgent
from .base_agent import BaseAgent
from .specialized_agents import (
    ActivityAgent, ProfileAgent, EventAgent, ReminderAgent, 
    InterestAgent, StudyAgent, create_agent, get_available_agents
)

# Storage managers
from .file_manager import MemoryFileManager
from .db_manager import MemoryDatabaseManager

# Embedding support
from .embeddings import EmbeddingClient, create_embedding_client, get_default_embedding_client

# LLM interface
from ..llm import BaseLLMClient

__all__ = [
    # Core memory classes
    "Memory",
    "ProfileMemory", 
    "EventMemory",
    
    # Agent architecture
    "MetaAgent",        # Main coordinator
    "BaseAgent",        # Base class for agents
    "ActivityAgent",    # Activity summarization
    "ProfileAgent",     # Character profile management
    "EventAgent",       # Event recording
    "ReminderAgent",    # Reminders and todos
    "InterestAgent",    # Interests and hobbies
    "StudyAgent",       # Learning and education
    "create_agent",     # Agent factory function
    "get_available_agents",  # List available agent types
    
    # Storage systems
    "MemoryFileManager",     # File-based storage
    "MemoryDatabaseManager", # Database storage with vectors
    
    # Embedding support
    "EmbeddingClient",
    "create_embedding_client", 
    "get_default_embedding_client",
    
    # LLM interface
    "BaseLLMClient",
]
