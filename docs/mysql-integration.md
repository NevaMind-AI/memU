# MySQL Database Integration

This document describes how to set up and use MySQL as a storage backend for MemU.

## Overview

MemU supports MySQL as an alternative to the default in-memory storage or PostgreSQL. MySQL integration allows you to:

- Persist memory data across application restarts
- Synchronize memory data for import, export, and backup use cases
- Scale memory storage for production deployments

## Requirements

### Dependencies

Install the MySQL driver:

```bash
pip install pymysql
# or
pip install mysqlclient
```

The MySQL integration uses SQLAlchemy and SQLModel, which are already included in MemU's dependencies.

### MySQL Server

You need a running MySQL server (version 5.7+ or 8.0+ recommended).

## Configuration

### Basic Setup

Configure MemU to use MySQL by setting the `metadata_store` provider:

```python
from memu.app.settings import DatabaseConfig, MetadataStoreConfig

config = DatabaseConfig(
    metadata_store=MetadataStoreConfig(
        provider="mysql",
        dsn="mysql+pymysql://user:password@localhost:3306/memu_db",
        ddl_mode="create",  # "create" or "validate"
    )
)
```

### Connection String Format

The DSN (Data Source Name) follows SQLAlchemy's URL format:

```
mysql+pymysql://username:password@host:port/database
```

Examples:
- Local: `mysql+pymysql://root:password@localhost:3306/memu`
- Remote: `mysql+pymysql://user:pass@db.example.com:3306/memu_prod`
- With charset: `mysql+pymysql://user:pass@localhost/memu?charset=utf8mb4`

### DDL Modes

- `create`: Automatically creates tables if they don't exist (default)
- `validate`: Only validates that expected tables exist, raises error if missing

## Usage

### With MemoryService

```python
from memu import MemoryService
from memu.app.settings import DatabaseConfig, MetadataStoreConfig

# Configure MySQL backend
db_config = DatabaseConfig(
    metadata_store=MetadataStoreConfig(
        provider="mysql",
        dsn="mysql+pymysql://user:password@localhost/memu_db",
    )
)

# Create service with MySQL storage
service = MemoryService(database=db_config)

# Use normally - data persists to MySQL
await service.memorize("User prefers dark mode")
results = await service.retrieve("What are the user's preferences?")
```

### Direct Store Access

```python
from memu.database.mysql import build_mysql_database
from memu.app.settings import DatabaseConfig, MetadataStoreConfig
from pydantic import BaseModel

class UserModel(BaseModel):
    user_id: str

config = DatabaseConfig(
    metadata_store=MetadataStoreConfig(
        provider="mysql",
        dsn="mysql+pymysql://user:password@localhost/memu_db",
    )
)

store = build_mysql_database(config=config, user_model=UserModel)

# Access repositories directly
items = store.memory_item_repo.list_items()
categories = store.memory_category_repo.list_categories()
```

## Database Schema

The MySQL integration creates the following tables:

### `resources`
Stores resource metadata (files, URLs, etc.)

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key (UUID) |
| url | VARCHAR(2048) | Resource URL |
| modality | VARCHAR(64) | Resource type |
| local_path | VARCHAR(1024) | Local file path |
| caption | TEXT | Optional caption |
| embedding | TEXT | JSON-encoded embedding vector |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

### `memory_items`
Stores individual memory items

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key (UUID) |
| resource_id | VARCHAR(36) | Foreign key to resources |
| memory_type | VARCHAR(32) | Type (profile/event/knowledge/behavior) |
| summary | TEXT | Memory content |
| embedding | TEXT | JSON-encoded embedding vector |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

### `memory_categories`
Stores memory categories

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key (UUID) |
| name | VARCHAR(255) | Category name |
| description | TEXT | Category description |
| embedding | TEXT | JSON-encoded embedding vector |
| summary | TEXT | Category summary |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

### `category_items`
Links memory items to categories

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key (UUID) |
| item_id | VARCHAR(36) | Foreign key to memory_items |
| category_id | VARCHAR(36) | Foreign key to memory_categories |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

## Vector Search

MySQL does not have native vector support like PostgreSQL's pgvector. The MySQL integration uses:

- **Storage**: Embeddings are stored as JSON-encoded TEXT
- **Search**: Brute-force cosine similarity computed in Python

For large-scale deployments requiring fast vector search, consider:
- Using PostgreSQL with pgvector
- Adding a dedicated vector database alongside MySQL

## Data Import/Export

### Export to MySQL

```python
# Migrate from in-memory to MySQL
from memu import MemoryService

# Source (in-memory)
source = MemoryService()
await source.memorize("Important memory 1")
await source.memorize("Important memory 2")

# Destination (MySQL)
dest = MemoryService(
    database=DatabaseConfig(
        metadata_store=MetadataStoreConfig(
            provider="mysql",
            dsn="mysql+pymysql://user:pass@localhost/memu_db",
        )
    )
)

# Copy data
for item in source.db.items.values():
    dest.db.memory_item_repo.create_item(
        resource_id=item.resource_id,
        memory_type=item.memory_type,
        summary=item.summary,
        embedding=item.embedding,
        user_data={},
    )
```

### Backup

Use standard MySQL backup tools:

```bash
# Backup
mysqldump -u user -p memu_db > memu_backup.sql

# Restore
mysql -u user -p memu_db < memu_backup.sql
```

## Troubleshooting

### Connection Issues

1. Verify MySQL server is running
2. Check credentials and host/port
3. Ensure database exists: `CREATE DATABASE memu_db;`
4. Check firewall rules for remote connections

### Character Encoding

For full Unicode support, use utf8mb4:

```sql
CREATE DATABASE memu_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Or in connection string:
```
mysql+pymysql://user:pass@localhost/memu_db?charset=utf8mb4
```

### Performance

For better performance:
- Add indexes on frequently queried columns
- Use connection pooling (configured by default)
- Consider read replicas for heavy read workloads
