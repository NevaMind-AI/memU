# User and Agent ID Support with Persistent Storage

This document explains the new user_id and agent_id support in MemU, along with SQLite and vector database persistence.

## Overview

MemU now supports multi-user and multi-agent scenarios with persistent storage:

- **User ID**: Identifies the end user interacting with the system
- **Agent ID**: Identifies the AI agent/assistant serving the user
- **SQLite**: Stores memory metadata (resources, items, categories, relationships)
- **Vector Database**: Stores embeddings for semantic search

## Key Features

### 1. Multi-User Support

Each user has their own isolated memory space:

```python
# User Alice
service_alice = MemoryService(
    user_id="alice",
    agent_id="assistant_v1",
    database_config=DatabaseConfig(
        provider="sqlite",
        sqlite_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    ),
)

# User Bob
service_bob = MemoryService(
    user_id="bob",
    agent_id="assistant_v1",
    database_config=DatabaseConfig(
        provider="sqlite",
        sqlite_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    ),
)
```

### 2. Multi-Agent Support

Each user can have multiple specialized agents:

```python
# General assistant for Charlie
service_general = MemoryService(
    user_id="charlie",
    agent_id="general_assistant",
    database_config=DatabaseConfig(provider="sqlite"),
)

# Coding assistant for Charlie
service_coding = MemoryService(
    user_id="charlie",
    agent_id="coding_assistant",
    database_config=DatabaseConfig(provider="sqlite"),
)
```

### 3. Persistent Storage

All data is automatically persisted to SQLite and vector databases:

- Resources (URLs, modalities, local paths)
- Memory items (summaries, types)
- Categories (names, descriptions, summaries)
- Relationships (category-item links)
- Embeddings (for semantic search)

### 4. Data Isolation

Data is isolated by `user_id` and `agent_id`:

- Each (user_id, agent_id) pair has its own memory space
- Queries only return data for the current user-agent pair
- No cross-contamination between users or agents

## Database Schema

### SQLite Tables

#### resources
- `id` (TEXT PRIMARY KEY)
- `user_id` (TEXT NOT NULL)
- `agent_id` (TEXT NOT NULL)
- `url` (TEXT NOT NULL)
- `modality` (TEXT NOT NULL)
- `local_path` (TEXT NOT NULL)
- `caption` (TEXT)
- `created_at` (REAL NOT NULL)
- **Unique constraint**: (user_id, agent_id, url)

#### memory_items
- `id` (TEXT PRIMARY KEY)
- `user_id` (TEXT NOT NULL)
- `agent_id` (TEXT NOT NULL)
- `resource_id` (TEXT NOT NULL, FOREIGN KEY)
- `memory_type` (TEXT NOT NULL)
- `summary` (TEXT NOT NULL)
- `created_at` (REAL NOT NULL)

#### categories
- `id` (TEXT PRIMARY KEY)
- `user_id` (TEXT NOT NULL)
- `agent_id` (TEXT NOT NULL)
- `name` (TEXT NOT NULL)
- `description` (TEXT NOT NULL)
- `summary` (TEXT)
- `created_at` (REAL NOT NULL)
- **Unique constraint**: (user_id, agent_id, name)

#### category_items
- `item_id` (TEXT NOT NULL, FOREIGN KEY)
- `category_id` (TEXT NOT NULL, FOREIGN KEY)
- `user_id` (TEXT NOT NULL)
- `agent_id` (TEXT NOT NULL)
- **Primary key**: (item_id, category_id)

### Vector Database

Stores embeddings in JSON format with three collections:
- `resources`: Resource caption embeddings
- `items`: Memory item embeddings
- `categories`: Category embeddings

Each entry contains:
- `user_id`: User identifier
- `agent_id`: Agent identifier
- `vector`: Embedding vector (list of floats)

## Usage Examples

### Basic Usage

```python
import asyncio
from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig

async def main():
    # Initialize service with user_id and agent_id
    service = MemoryService(
        user_id="user123",
        agent_id="assistant_v1",
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

    # Add memory
    result = await service.memorize(
        resource_url="path/to/conversation.txt",
        modality="conversation",
    )

    # Retrieve memories
    queries = [{"role": "user", "content": {"text": "What do you know about me?"}}]
    retrieved = await service.retrieve(queries)

    print(f"Retrieved {len(retrieved['items'])} memory items")

asyncio.run(main())
```

### Database Migration

```python
from memu.storage.migrations import migrate_database, backup_database, reset_database

# Initialize database schema
migrate_database(
    db_path="./data/memu.db",
    vector_db_path="./data/vectors.json",
)

# Create backup
backup_database(
    db_path="./data/memu.db",
    vector_db_path="./data/vectors.json",
    backup_path="./data/backups",
)

# Reset database (caution: deletes all data!)
# reset_database()
```

### In-Memory Mode (No Persistence)

For testing or temporary usage:

```python
service = MemoryService(
    user_id="temp_user",
    agent_id="temp_agent",
    database_config=DatabaseConfig(
        provider="memory",  # No persistence
    ),
)
```

## Configuration

### Database Configuration

```python
from memu.app.settings import DatabaseConfig

# SQLite + Vector DB (Persistent)
config = DatabaseConfig(
    provider="sqlite",
    sqlite_path="./data/memu.db",
    vector_db_path="./data/vectors.json",
)

# In-Memory (No Persistence)
config = DatabaseConfig(
    provider="memory",
)
```

### Complete Service Configuration

```python
from memu.app.service import MemoryService
from memu.app.settings import BlobConfig, DatabaseConfig, LLMConfig

service = MemoryService(
    user_id="user123",
    agent_id="assistant_v1",
    llm_config=LLMConfig(
        base_url="https://api.openai.com/v1",
        api_key="YOUR_API_KEY",
        chat_model="gpt-4o-mini",
        embed_model="text-embedding-3-small",
    ),
    blob_config=BlobConfig(
        provider="local",
        resources_dir="./data/resources",
    ),
    database_config=DatabaseConfig(
        provider="sqlite",
        sqlite_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    ),
)
```

## Migration from Older Versions

If you're upgrading from a version without user_id/agent_id:

1. **Default Values**: The system uses "default" for user_id and agent_id if not specified
2. **Backward Compatibility**: InMemoryStore still works but requires user_id/agent_id parameters
3. **Data Migration**: Run `migrate_database()` to initialize the new schema

### Legacy Code Compatibility

Old code without user_id/agent_id:

```python
# Old code (still works with defaults)
service = MemoryService()  # Uses user_id="default", agent_id="default"
```

New code with explicit IDs:

```python
# New code (recommended)
service = MemoryService(
    user_id="user123",
    agent_id="assistant_v1",
)
```

## Performance Considerations

### SQLite

- Automatic indexing on (user_id, agent_id) columns
- Foreign key constraints ensure data integrity
- Transaction-based writes for consistency

### Vector Database

- In-memory indexing for fast queries
- JSON persistence for durability
- Cosine similarity for semantic search
- Filtered by user_id and agent_id

### Scalability

For production use with many users:

1. Consider using a more robust vector database (e.g., Pinecone, Weaviate, Qdrant)
2. Implement connection pooling for SQLite
3. Add caching layer for frequently accessed data
4. Consider sharding by user_id for very large datasets

## API Changes

### Models

All models now include `user_id` and `agent_id`:

- `Resource`
- `MemoryItem`
- `MemoryCategory`
- `CategoryItem`

### Store Methods

Store methods now require or accept `user_id` and `agent_id`:

```python
# InMemoryStore
store.create_resource(..., user_id="...", agent_id="...")
store.create_item(..., user_id="...", agent_id="...")
store.get_or_create_category(..., user_id="...", agent_id="...")
store.link_item_category(..., user_id="...", agent_id="...")

# PersistentStore
store = PersistentStore(db=db, vector_db=vector_db, user_id="...", agent_id="...")
# Methods use the store's user_id and agent_id automatically
```

## Testing

See `examples/user_agent_example.py` for comprehensive examples:

```bash
python examples/user_agent_example.py
```

## Security Considerations

1. **Data Isolation**: Enforce user_id/agent_id checks in all queries
2. **Authentication**: Implement proper authentication to verify user_id
3. **Authorization**: Verify users can only access their own data
4. **Encryption**: Consider encrypting sensitive data at rest
5. **Backup**: Regularly backup databases to prevent data loss

## Troubleshooting

### Database Locked Error

If you encounter "database is locked" errors:

```python
# Use WAL mode for better concurrency
import sqlite3
conn = sqlite3.connect("./data/memu.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.close()
```

### Vector DB Performance

For large vector databases (>10,000 vectors):

- Consider using a specialized vector database
- Implement approximate nearest neighbor search (ANN)
- Add caching for frequently queried vectors

### Memory Issues

If experiencing memory issues with large datasets:

- Use pagination for queries
- Implement lazy loading for resources
- Clear caches periodically
- Consider using generators for large result sets

## Future Enhancements

Planned improvements:

1. **Multi-tenancy**: Organization-level isolation
2. **Vector DB Backends**: Support for Pinecone, Weaviate, Qdrant
3. **Database Backends**: Support for PostgreSQL, MySQL
4. **Caching Layer**: Redis integration for better performance
5. **Batch Operations**: Bulk insert/update for efficiency
6. **Data Export**: Export user data in standard formats
7. **Analytics**: Usage statistics and insights per user/agent
