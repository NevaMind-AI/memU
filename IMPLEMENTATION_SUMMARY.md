# MemU - User ID and Agent ID Support Implementation Summary

## Overview

This implementation adds comprehensive support for multi-user and multi-agent scenarios with persistent storage using SQLite and a simple vector database.

## Changes Made

### 1. Updated Models (`src/memu/models.py`)
- Added `user_id`, `agent_id`, and `created_at` fields to all models:
  - `Resource`
  - `MemoryItem`
  - `MemoryCategory`
  - `CategoryItem`

### 2. Created Storage Backends

#### SQLite Database (`src/memu/storage/sqlite_db.py`)
- `SQLiteDB` class for persistent metadata storage
- Tables: `resources`, `memory_items`, `categories`, `category_items`
- Automatic indexing on `(user_id, agent_id)` columns
- Foreign key constraints for data integrity

#### Vector Database (`src/memu/storage/vector_db.py`)
- `SimpleVectorDB` class for embedding storage
- JSON-based persistence
- Cosine similarity search
- Collections: `resources`, `items`, `categories`

#### Migration Utilities (`src/memu/storage/migrations.py`)
- `migrate_database()`: Initialize schema
- `backup_database()`: Create backups
- `reset_database()`: Reset database

### 3. Updated Repository (`src/memu/memory/repo.py`)

#### New: PersistentStore
- Backed by SQLite + Vector DB
- Automatic persistence of all operations
- In-memory caching for performance
- Loads existing data on initialization

#### Updated: InMemoryStore
- Backward compatible
- Added optional `user_id` and `agent_id` parameters
- Defaults to "default" for both

### 4. Updated MemoryService (`src/memu/app/service.py`)

#### Constructor Changes
- Added `user_id` and `agent_id` parameters
- Auto-initializes storage based on `database_config.provider`
- Supports both "memory" and "sqlite" providers

#### Method Updates
- All resource/item/category operations now pass `user_id` and `agent_id`
- Resource embeddings are persisted to vector DB
- Category summaries are persisted to SQLite

### 5. Updated Settings (`src/memu/app/settings.py`)
- Enhanced `DatabaseConfig`:
  - `provider`: "memory" or "sqlite"
  - `sqlite_path`: Path to SQLite database
  - `vector_db_path`: Path to vector database

### 6. Documentation

#### User Guide (`docs/USER_AGENT_SUPPORT.md`)
- Complete documentation of new features
- Usage examples
- Configuration guide
- Migration guide
- Performance considerations
- Security considerations

#### Example Code (`examples/user_agent_example.py`)
- 5 comprehensive examples:
  1. Single user and agent with persistence
  2. Multiple users with same agent
  3. Multiple agents for same user
  4. Database migration and backup
  5. In-memory mode

#### Tests (`tests/test_user_agent_storage.py`)
- Unit tests for SQLiteDB
- Unit tests for SimpleVectorDB
- Unit tests for PersistentStore
- Unit tests for InMemoryStore backward compatibility
- Data isolation tests

### 7. Package Structure
- Created `src/memu/storage/__init__.py` for cleaner imports

## Key Features

### Data Isolation
- Complete isolation between `(user_id, agent_id)` pairs
- No cross-contamination of data
- Separate vector spaces per user-agent

### Backward Compatibility
- Existing code continues to work
- Default values: `user_id="default"`, `agent_id="default"`
- InMemoryStore still available for testing

### Performance
- In-memory caching for fast access
- Indexed queries on user_id and agent_id
- Efficient vector search with filtering

### Persistence
- All data automatically saved to SQLite
- Embeddings saved to vector DB
- Crash-resistant with transaction support

## Usage Example

```python
from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig

# Initialize service with user_id and agent_id
service = MemoryService(
    user_id="alice",
    agent_id="assistant_v1",
    database_config=DatabaseConfig(
        provider="sqlite",
        sqlite_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    ),
)

# All operations are automatically isolated by user_id and agent_id
result = await service.memorize(
    resource_url="conversation.txt",
    modality="conversation",
)

queries = [{"role": "user", "content": {"text": "What did we discuss?"}}]
retrieved = await service.retrieve(queries)
```

## Testing

Run tests with:
```bash
pytest tests/test_user_agent_storage.py -v
```

Run example:
```bash
python examples/user_agent_example.py
```

## Migration Path

### From In-Memory to Persistent

```python
# Old code (in-memory)
service = MemoryService()

# New code (persistent)
service = MemoryService(
    user_id="user123",
    agent_id="assistant_v1",
    database_config=DatabaseConfig(provider="sqlite"),
)
```

### Database Initialization

```python
from memu.storage.migrations import migrate_database

# Initialize database schema
migrate_database()
```

## File Structure

```
src/memu/
├── models.py                    # Updated with user_id/agent_id
├── app/
│   ├── service.py              # Updated MemoryService
│   └── settings.py             # Enhanced DatabaseConfig
├── memory/
│   └── repo.py                 # PersistentStore + InMemoryStore
└── storage/
    ├── __init__.py             # Package exports
    ├── sqlite_db.py            # SQLite backend
    ├── vector_db.py            # Vector database
    ├── migrations.py           # Migration utilities
    └── local_fs.py             # File storage (unchanged)

docs/
└── USER_AGENT_SUPPORT.md       # Complete documentation

examples/
└── user_agent_example.py       # Usage examples

tests/
└── test_user_agent_storage.py # Comprehensive tests
```

## Next Steps

1. **Test the implementation**:
   ```bash
   pytest tests/test_user_agent_storage.py
   ```

2. **Run examples**:
   ```bash
   python examples/user_agent_example.py
   ```

3. **Initialize database**:
   ```python
   from memu.storage.migrations import migrate_database
   migrate_database()
   ```

4. **Update your code** to use `user_id` and `agent_id`:
   ```python
   service = MemoryService(
       user_id="your_user_id",
       agent_id="your_agent_id",
       database_config=DatabaseConfig(provider="sqlite"),
   )
   ```

## Performance Characteristics

- **SQLite**: ~1000 writes/sec, unlimited reads
- **Vector DB**: In-memory search, O(n) similarity for small datasets
- **Recommended**: < 10,000 vectors per user-agent pair

For larger scales:
- Use dedicated vector DB (Pinecone, Weaviate, Qdrant)
- Implement connection pooling
- Add caching layer (Redis)

## Security Considerations

1. Always validate `user_id` and `agent_id` from authenticated sessions
2. Don't trust client-provided IDs without verification
3. Consider encrypting sensitive data at rest
4. Implement rate limiting per user
5. Regular backups of databases

## Support

For issues or questions:
- GitHub Issues: https://github.com/NevaMind-AI/MemU/issues
- Discord: https://discord.gg/memu
- Documentation: docs/USER_AGENT_SUPPORT.md
