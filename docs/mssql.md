# Microsoft SQL Server (MSSQL) Integration

MemU supports Microsoft SQL Server (MSSQL) as a robust, enterprise-grade database backend for memory storage. This is ideal for:

- **Enterprise environments** with existing SQL Server infrastructure
- **High-concurrency applications** requiring strong consistency
- **Complex data modeling** and reporting needs
- **Scalable deployments** managed by IT/Ops teams

## Quick Start

### Prerequisites

> [!WARNING]
> The MSSQL integration relies on `pyodbc`, which requires system-level ODBC drivers.

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install unixodbc-dev
```

**Windows:**
Ensure you have the standard **ODBC Driver for SQL Server** installed (typically included with SSMS or available from Microsoft).

### Installation

Add the `pyodbc` dependency to your project:

```bash
uv add pyodbc
```

### Basic Configuration

```python
from memu.app import MemoryService

# Example using a connection string
service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {
            "provider": "mssql",
            "dsn": "mssql+pyodbc://sa:your_password@localhost/memu?driver=ODBC+Driver+17+for+SQL+Server",
        },
    },
)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `provider` | `str` | N/A | Set to `"mssql"` to use MSSQL backend |
| `dsn` | `str` | N/A | SQLAlchemy-compatible connection string |

### DSN Format

The DSN follows the SQLAlchemy format for `pyodbc`:
`mssql+pyodbc://<username>:<password>@<host>/<database>?driver=<driver_name>`

Example:
`mssql+pyodbc://sa:StrongPass123!@localhost/memu?driver=ODBC+Driver+17+for+SQL+Server`

## Vector Search

MSSQL does not have a native vector search standard equivalent to `pgvector` enabled by default in all versions. MemU currently supports specific configurations or falls back to handling embeddings via:

1.  **Brute-force (in-memory)**: Like SQLite, if no vector index provider is configured.
2.  **External Index**: You can configure a separate vector provider (e.g., Qdrant, Milvus) while using MSSQL for metadata.

```python
service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {
            "provider": "mssql",
            "dsn": "mssql+pyodbc://...",
        },
        "vector_index": {
            "provider": "bruteforce",  # Default if no specialized MSSQL vector extension is used
        },
    },
)
```

## Database Schema

MemU creates the following tables automatically via `SQLModel`:

- `resources` - Multimodal resource records
- `memory_items` - Extracted memory items with embeddings
- `memory_categories` - Memory categories with summaries
- `category_items` - Relationships between items and categories

## Testing

You can use the included mock tests to verify the integration logic without a running database instance:

```bash
uv run pytest tests/test_mssql_mock.py
```

## Troubleshooting

### Driver Not Found

If you see errors related to "Data source name not found and no default driver specified":
1.  Verify the `driver` parameter in your DSN matches the installed driver name (check ODBC Data Source Administrator on Windows or `/etc/odbcinst.ini` on Linux).
2.  Ensure `unixodbc-dev` is installed on Linux.

### Connection Timeout

Ensure TCP/IP is enabled in SQL Server Configuration Manager and the port (default 1433) is open.
