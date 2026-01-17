# Oracle Database Provider

MemU supports Oracle Database as a backend for storing memories.

## Installation

To enable the Oracle provider, you must install the `oracledb` dependency.

```bash
uv add oracledb
```

## Configuration

You can configure the Oracle repository by instantiating it with your credentials:

```python
from memu.database.oracle import OracleMemoryItemRepo

# Using explicit credentials and DSN
repo = OracleMemoryItemRepo(
    user="myuser",
    password="mypassword",
    dsn="localhost:1521/XEPDB1"
)

# Using wallet or other connection methods supported by python-oracledb
# For thick mode (required for some advanced features), ensure Instant Client is installed
# and initialized before creating the repo.
import oracledb
# oracledb.init_oracle_client(lib_dir="/path/to/instantclient")
```

## Features

- **Storage**: Full support for `MemoryItem`, `MemoryCategory`, and `CategoryItem`.
- **Embeddings**: Stored as JSON CLOBs (Vector type support pending).
- **Strict Typing**: Fully typed and compliant with MemU protocols.

## Limitations

- **Vector Search**: Currently raises `NotImplementedError`. Implementation requires Oracle Database 23ai or newer with Vector support enabled, or a custom PL/SQL implementation which is not currently included.
