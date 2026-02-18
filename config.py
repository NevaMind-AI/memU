# MemU + OpenClaw Integration Configuration

# This configuration file defines the complete setup for integrating
# MemU memory framework with OpenClaw for proactive memory management.

import os
from pathlib import Path
from memu.app.settings import (
    DatabaseConfig,
    MetadataStoreConfig,
    VectorIndexConfig,
    LLMProfilesConfig,
    LLMConfig,
    MemorizeConfig,
    RetrieveConfig,
    CategoryConfig,
    UserConfig,
    DefaultUserModel
)

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RESOURCES_DIR = DATA_DIR / "resources"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
RESOURCES_DIR.mkdir(exist_ok=True)

# Database Configuration
DATABASE_CONFIG = DatabaseConfig(
    metadata_store=MetadataStoreConfig(
        provider="sqlite",  # Options: "inmemory", "postgres", "sqlite"
        ddl_mode="create",
        dsn="sqlite:///data/memu.db"  # Use local SQLite file
    ),
    vector_index=VectorIndexConfig(
        provider="bruteforce",  # Options: "bruteforce", "pgvector", "none"
        dsn=os.getenv("MEMU_VECTOR_URL")  # Only needed for pgvector
    )
)

# LLM Profiles Configuration - Pointing to OpenClaw Bridge
LLM_PROFILES = LLMProfilesConfig({
    "default": LLMConfig(
        provider="openai",  # Using OpenAI-compatible bridge
        base_url="http://localhost:5000/v1",  # OpenClaw bridge endpoint
        api_key="dummy",  # Dummy key for the bridge
        chat_model="openclaw-bridge",
        client_backend="sdk",  # Using OpenAI SDK format
        embed_model="fake-embeddings",  # Using fake embeddings through bridge
        embed_batch_size=1
    ),
    "embedding": LLMConfig(
        provider="openai",
        base_url="http://localhost:5000/v1",
        api_key="dummy",
        chat_model="openclaw-bridge",
        client_backend="sdk",
        embed_model="fake-embeddings",
        embed_batch_size=1
    )
})

# Memory Categories - Auto-generated from user interactions
MEMORY_CATEGORIES = [
    CategoryConfig(
        name="personal_info",
        description="Personal information about the user and their preferences"
    ),
    CategoryConfig(
        name="preferences", 
        description="User preferences, likes, dislikes, and behavioral patterns"
    ),
    CategoryConfig(
        name="relationships",
        description="Information about relationships with other people and entities"
    ),
    CategoryConfig(
        name="activities",
        description="Activities, hobbies, interests, and daily routines"
    ),
    CategoryConfig(
        name="goals",
        description="Goals, aspirations, objectives, and plans"
    ),
    CategoryConfig(
        name="experiences", 
        description="Past experiences, events, and memorable moments"
    ),
    CategoryConfig(
        name="knowledge",
        description="Knowledge, facts, learned information, and expertise"
    ),
    CategoryConfig(
        name="opinions",
        description="Opinions, viewpoints, perspectives, and beliefs"
    ),
    CategoryConfig(
        name="habits",
        description="Habits, routines, patterns, and regular behaviors"
    ),
    CategoryConfig(
        name="work_life",
        description="Work-related information, professional life, and career"
    ),
    # Additional categories for OpenClaw-specific data
    CategoryConfig(
        name="hle_analysis",
        description="HLE (Holistic Language Education) challenge analyses and solutions"
    ),
    CategoryConfig(
        name="system_operations",
        description="System operations, maintenance, and autonomous decision making"
    ),
    CategoryConfig(
        name="autonomous_behavior",
        description="Autonomous behaviors, self-modifications, and proactive actions"
    )
]

# Memorize Configuration
MEMORIZE_CONFIG = MemorizeConfig(
    memory_categories=MEMORY_CATEGORIES,
    category_assign_threshold=0.25,
    memory_types=["profile", "event", "knowledge", "behavior", "skill"],
    preprocess_llm_profile="default",
    memory_extract_llm_profile="default",
    category_update_llm_profile="default"
)

# Retrieve Configuration  
RETRIEVE_CONFIG = RetrieveConfig(
    method="rag",  # Use RAG for proactive context loading
    category=dict(enabled=True, top_k=5),
    item=dict(enabled=True, top_k=10),
    resource=dict(enabled=True, top_k=3),
    sufficiency_check=True
)

# User Configuration
USER_CONFIG = UserConfig(
    model=DefaultUserModel
)

# Blob Configuration
BLOB_CONFIG = {
    "provider": "local",
    "resources_dir": str(RESOURCES_DIR)
}

# Complete Service Configuration
SERVICE_CONFIG = {
    "llm_profiles": LLM_PROFILES,
    "database_config": DATABASE_CONFIG,
    "memorize_config": MEMORIZE_CONFIG,
    "retrieve_config": RETRIEVE_CONFIG,
    "user_config": USER_CONFIG,
    "blob_config": BLOB_CONFIG
}

# OpenClaw Bridge Settings
OPENCLAW_SETTINGS = {
    "bridge_port": 5000,
    "bridge_host": "localhost",
    "openclaw_executable": "node",
    "openclaw_script": r"C:\Users\16663\Desktop\openclaw\openclaw.mjs",
    "session_id": "memu_bridge",
    "thinking_mode": "low"
}

# Proactive Memory Settings
PROACTIVE_SETTINGS = {
    "enabled": True,
    "scan_interval_seconds": 300,  # Scan every 5 minutes
    "auto_commit_enabled": True,
    "memory_retention_days": 30,
    "consolidation_frequency": "daily"
}

print("MemU + OpenClaw Configuration loaded successfully")
print(f"Data directory: {DATA_DIR}")
print(f"Bridge endpoint: http://{OPENCLAW_SETTINGS['bridge_host']}:{OPENCLAW_SETTINGS['bridge_port']}/v1")
print(f"Database provider: {DATABASE_CONFIG.metadata_store.provider}")
print(f"Memory categories: {len(MEMORY_CATEGORIES)} defined")