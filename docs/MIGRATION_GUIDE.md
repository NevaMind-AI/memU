# Migration Guide: Upgrading to User/Agent ID Support

This guide helps you upgrade your existing MemU code to use the new user_id and agent_id features with persistent storage.

## Quick Start

### For New Projects

If you're starting a new project, simply initialize MemoryService with user_id and agent_id:

```python
from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig

service = MemoryService(
    user_id="your_user_id",
    agent_id="your_agent_id",
    database_config=DatabaseConfig(
        provider="sqlite",
        sqlite_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    ),
)
```

### For Existing Projects

Your existing code will continue to work with default values:

```python
# Old code - still works!
service = MemoryService()

# Equivalent to:
service = MemoryService(
    user_id="default",
    agent_id="default",
    database_config=DatabaseConfig(provider="memory"),
)
```

## Step-by-Step Migration

### Step 1: Update Your Dependencies

```bash
pip install --upgrade memu-py
```

### Step 2: Initialize Database (for persistent storage)

```python
from memu.storage.migrations import migrate_database

# Create database schema
migrate_database(
    db_path="./data/memu.db",
    vector_db_path="./data/vectors.json",
)
```

### Step 3: Update Your Code

#### Option A: Minimal Changes (Keep In-Memory)

No changes needed! Your code continues to work with in-memory storage.

#### Option B: Add Persistence

Update your service initialization:

```python
# Before
from memu.app.service import MemoryService

service = MemoryService(
    llm_config={
        "api_key": "YOUR_API_KEY",
        "chat_model": "gpt-4o-mini",
    },
)

# After
from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig

service = MemoryService(
    user_id="user123",           # NEW: Add user ID
    agent_id="assistant_v1",     # NEW: Add agent ID
    llm_config={
        "api_key": "YOUR_API_KEY",
        "chat_model": "gpt-4o-mini",
    },
    database_config=DatabaseConfig(  # NEW: Add database config
        provider="sqlite",
        sqlite_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    ),
)
```

#### Option C: Multi-User Support

If you're building a multi-user application:

```python
def create_service_for_user(user_id: str, agent_id: str = "default_agent"):
    """Create a MemoryService instance for a specific user."""
    return MemoryService(
        user_id=user_id,
        agent_id=agent_id,
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

# Usage
alice_service = create_service_for_user("alice")
bob_service = create_service_for_user("bob")
```

### Step 4: Test Your Migration

Create a simple test script:

```python
import asyncio
from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig

async def test_migration():
    # Create service
    service = MemoryService(
        user_id="test_user",
        agent_id="test_agent",
        database_config=DatabaseConfig(provider="sqlite"),
    )

    # Test memorize
    result = await service.memorize(
        resource_url="test_data.txt",
        modality="document",
    )
    print(f"Created {len(result['items'])} items")

    # Test retrieve
    queries = [{"role": "user", "content": {"text": "Test query"}}]
    retrieved = await service.retrieve(queries)
    print(f"Retrieved {len(retrieved['items'])} items")

asyncio.run(test_migration())
```

## Common Migration Scenarios

### Scenario 1: Personal Assistant App

```python
# Single user, single agent
service = MemoryService(
    user_id="john_doe",
    agent_id="personal_assistant",
    database_config=DatabaseConfig(provider="sqlite"),
)
```

### Scenario 2: Multi-User SaaS Platform

```python
class MemoryManager:
    def __init__(self, db_path: str = "./data/memu.db"):
        self.db_path = db_path
        self.services = {}

    def get_service(self, user_id: str, agent_id: str = "default"):
        key = (user_id, agent_id)
        if key not in self.services:
            self.services[key] = MemoryService(
                user_id=user_id,
                agent_id=agent_id,
                database_config=DatabaseConfig(
                    provider="sqlite",
                    sqlite_path=self.db_path,
                ),
            )
        return self.services[key]

# Usage
manager = MemoryManager()
service = manager.get_service(user_id=request.user.id)
```

### Scenario 3: Multi-Agent System

```python
# Create specialized agents for the same user
user_id = "alice"

general_agent = MemoryService(
    user_id=user_id,
    agent_id="general_assistant",
    database_config=DatabaseConfig(provider="sqlite"),
)

coding_agent = MemoryService(
    user_id=user_id,
    agent_id="coding_assistant",
    database_config=DatabaseConfig(provider="sqlite"),
)

research_agent = MemoryService(
    user_id=user_id,
    agent_id="research_assistant",
    database_config=DatabaseConfig(provider="sqlite"),
)
```

## Data Migration

### Migrating Existing In-Memory Data

If you have existing data in InMemoryStore that you want to migrate to persistent storage:

```python
import asyncio
from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig

async def migrate_existing_data():
    # Old service (in-memory)
    old_service = MemoryService(
        database_config=DatabaseConfig(provider="memory"),
    )

    # ... load your existing data into old_service ...

    # New service (persistent)
    new_service = MemoryService(
        user_id="migrated_user",
        agent_id="migrated_agent",
        database_config=DatabaseConfig(provider="sqlite"),
    )

    # Copy resources
    for res_id, res in old_service.store.resources.items():
        new_res = new_service.store.create_resource(
            url=res.url,
            modality=res.modality,
            local_path=res.local_path,
        )
        if res.caption and res.embedding:
            new_res.caption = res.caption
            new_res.embedding = res.embedding
            new_service.store.update_resource_embedding(new_res.id, res.embedding)

    # Copy categories
    for cat_id, cat in old_service.store.categories.items():
        if cat.embedding:
            new_service.store.get_or_create_category(
                name=cat.name,
                description=cat.description,
                embedding=cat.embedding,
            )

    print("Migration completed!")

asyncio.run(migrate_existing_data())
```

## Troubleshooting

### Issue: "database is locked" Error

**Solution**: Use WAL mode for better concurrency:

```python
import sqlite3

conn = sqlite3.connect("./data/memu.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.close()
```

### Issue: Slow Vector Search

**Solution**: For large datasets (>10,000 vectors), consider:

1. Using a dedicated vector database (Pinecone, Weaviate, Qdrant)
2. Implementing pagination
3. Adding caching

### Issue: Data Not Persisting

**Checklist**:
1. Ensure `provider="sqlite"` in DatabaseConfig
2. Check file permissions on database paths
3. Verify paths are correct and writable
4. Check for exceptions during service initialization

### Issue: Memory Usage Too High

**Solution**: The current implementation loads all data into memory. For large datasets:

1. Implement lazy loading
2. Use pagination for queries
3. Clear caches periodically
4. Consider database sharding

## Best Practices

### 1. User ID Format

Use consistent, unique identifiers:

```python
# Good
user_id = str(uuid.uuid4())  # UUID
user_id = f"user_{user.id}"  # Database ID
user_id = user.email          # Email (if unique)

# Avoid
user_id = "user1"  # Too generic
user_id = user.name  # May not be unique
```

### 2. Agent ID Format

Use descriptive, consistent names:

```python
# Good
agent_id = "general_assistant_v1"
agent_id = "coding_helper"
agent_id = "research_bot"

# Avoid
agent_id = "agent1"  # Not descriptive
agent_id = "Bob"     # Confusing
```

### 3. Database Management

```python
from memu.storage.migrations import backup_database

# Regular backups
backup_database(
    db_path="./data/memu.db",
    vector_db_path="./data/vectors.json",
    backup_path=f"./data/backups/{datetime.now().isoformat()}",
)
```

### 4. Error Handling

```python
try:
    service = MemoryService(
        user_id=user_id,
        agent_id=agent_id,
        database_config=DatabaseConfig(provider="sqlite"),
    )
except Exception as e:
    logger.error(f"Failed to initialize service: {e}")
    # Fall back to in-memory
    service = MemoryService(
        user_id=user_id,
        agent_id=agent_id,
        database_config=DatabaseConfig(provider="memory"),
    )
```

### 5. Testing

Always test with isolated user/agent IDs:

```python
import pytest

@pytest.fixture
def test_service():
    import uuid
    test_id = str(uuid.uuid4())

    service = MemoryService(
        user_id=f"test_user_{test_id}",
        agent_id=f"test_agent_{test_id}",
        database_config=DatabaseConfig(provider="sqlite"),
    )

    yield service

    # Cleanup after test
    # (implement cleanup logic)
```

## Getting Help

- **Documentation**: See `docs/USER_AGENT_SUPPORT.md`
- **Examples**: See `examples/user_agent_example.py`
- **Tests**: See `tests/test_user_agent_storage.py`
- **GitHub Issues**: https://github.com/NevaMind-AI/MemU/issues
- **Discord**: https://discord.gg/memu

## Summary Checklist

- [ ] Update MemU to latest version
- [ ] Run `migrate_database()` if using persistent storage
- [ ] Update service initialization with `user_id` and `agent_id`
- [ ] Add `DatabaseConfig` with provider and paths
- [ ] Test memorize and retrieve operations
- [ ] Implement backup strategy
- [ ] Update error handling
- [ ] Test with multiple users/agents
- [ ] Read full documentation
- [ ] Run example code

Congratulations! You're now using MemU with user and agent ID support! 🎉
