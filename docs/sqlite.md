# SQLite Database Integration

MemU supports SQLite as a lightweight, file-based database backend for memory storage. This is ideal for:

- **Local development** and testing
- **Single-user applications** with persistent storage
- **Portable deployments** where you need a simple database solution
- **Offline-capable applications** that can't rely on external databases

## Quick Start

### Basic Configuration

```python
from memu.app import MemoryService

# Using default SQLite file (memu.db in current directory)
service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {
            "provider": "sqlite",
        },
    },
)

# Or specify a custom database path
service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {
            "provider": "sqlite",
            "dsn": "sqlite:///path/to/your/memory.db",
        },
    },
)
```

### In-Memory SQLite (No Persistence)

For testing or temporary storage, you can use an in-memory SQLite database:

```python
service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {
            "provider": "sqlite",
            "dsn": "sqlite:///:memory:",
        },
    },
)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `provider` | `str` | `"inmemory"` | Set to `"sqlite"` to use SQLite backend |
| `dsn` | `str` | `"sqlite:///memu.db"` | SQLite connection string |

### DSN Format

SQLite DSN follows this format:
- **File-based**: `sqlite:///path/to/database.db`
- **In-memory**: `sqlite:///:memory:`
- **Relative path**: `sqlite:///./data/memu.db`
- **Absolute path**: `sqlite:////home/user/data/memu.db` (note the 4 slashes)

## Vector Search

SQLite doesn't have native vector support like PostgreSQL's pgvector. MemU uses **brute-force cosine similarity** for vector search when using SQLite:

```python
service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {
            "provider": "sqlite",
            "dsn": "sqlite:///memu.db",
        },
        "vector_index": {
            "provider": "bruteforce",  # This is the default for SQLite
        },
    },
)
```

**Note**: Brute-force search loads all embeddings into memory and computes similarity for each. This works well for moderate dataset sizes (up to ~100k items) but may be slow for larger datasets.

## Database Schema

SQLite creates the following tables automatically:

- `sqlite_resources` - Multimodal resource records (images, documents, etc.)
- `sqlite_memory_items` - Extracted memory items with embeddings
- `sqlite_memory_categories` - Memory categories with summaries
- `sqlite_category_items` - Relationships between items and categories

Embeddings are stored as JSON-serialized text in SQLite since there's no native vector type.

## Data Import/Export

### Export Data

You can export your SQLite database for backup or migration:

```python
import shutil

# Simply copy the database file
shutil.copy("memu.db", "memu_backup.db")
```

### Import from SQLite to PostgreSQL

To migrate data from SQLite to PostgreSQL:

```python
import json
from memu.database.sqlite import build_sqlite_database
from memu.database.postgres import build_postgres_database
from memu.app.settings import DatabaseConfig
from pydantic import BaseModel

class UserScope(BaseModel):
    user_id: str

# Load from SQLite
sqlite_config = DatabaseConfig(
    metadata_store={"provider": "sqlite", "dsn": "sqlite:///memu.db"}
)
sqlite_db = build_sqlite_database(config=sqlite_config, user_model=UserScope)
sqlite_db.load_existing()

# Connect to PostgreSQL
postgres_config = DatabaseConfig(
    metadata_store={"provider": "postgres", "dsn": "postgresql://..."}
)
postgres_db = build_postgres_database(config=postgres_config, user_model=UserScope)

# Migrate resources
for res_id, resource in sqlite_db.resources.items():
    postgres_db.resource_repo.create_resource(
        url=resource.url,
        modality=resource.modality,
        local_path=resource.local_path,
        caption=resource.caption,
        embedding=resource.embedding,
        user_data={"user_id": getattr(resource, "user_id", None)},
    )

# Similar for categories, items, and relations...
```

## Performance Considerations

| Aspect | SQLite | PostgreSQL |
|--------|--------|------------|
| Setup | Zero configuration | Requires server setup |
| Concurrency | Single writer, multiple readers | Full concurrent access |
| Vector Search | Brute-force (in-memory) | Native pgvector (indexed) |
| Scale | Up to ~100k items | Millions of items |
| Deployment | Single file, portable | External service |

## Example: Full Workflow

```python
import asyncio
from memu.app import MemoryService

async def main():
    # Initialize with SQLite
    service = MemoryService(
        llm_profiles={"default": {"api_key": "your-api-key"}},
        database_config={
            "metadata_store": {
                "provider": "sqlite",
                "dsn": "sqlite:///my_memories.db",
            },
        },
    )

    # Memorize a conversation
    result = await service.memorize(
        resource_url="conversation.json",
        modality="conversation",
        user={"user_id": "alice"},
    )
    print(f"Created {len(result['categories'])} categories")

    # Retrieve relevant memories
    memories = await service.retrieve(
        queries=[
            {"role": "user", "content": {"text": "What are my preferences?"}}
        ],
        where={"user_id": "alice"},
    )

    for item in memories.get("items", []):
        print(f"- {item['summary']}")

asyncio.run(main())
```

## Troubleshooting

### Database Locked Error

SQLite only allows one writer at a time. If you see "database is locked" errors:

1. Ensure you're not running multiple processes writing to the same database
2. Consider using PostgreSQL for concurrent access needs
3. Use connection pooling with appropriate timeouts

### Permission Denied

Make sure the directory containing the SQLite file is writable:

```bash
chmod 755 /path/to/data/directory
```

### Slow Vector Search

If vector search is slow with large datasets:

1. Consider migrating to PostgreSQL with pgvector
2. Use more selective `where` filters to reduce the search space
3. Reduce `top_k` parameters in your retrieve configuration
