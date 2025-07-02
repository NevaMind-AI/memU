# PostgreSQL + pgvector Migration Guide for PersonaLab

PersonaLab now supports PostgreSQL with pgvector extension as an alternative to SQLite for improved performance, scalability, and native vector operations.

## 🚀 Benefits of PostgreSQL + pgvector

### Performance Benefits
- **Native Vector Operations**: No Python-based similarity calculations
- **HNSW Indexing**: Hierarchical Navigable Small World indexes for fast vector search
- **Concurrent Access**: Multiple users can access the system simultaneously
- **ACID Transactions**: Data consistency and reliability
- **Better Scalability**: Handle larger datasets efficiently

### Feature Benefits
- **Advanced Vector Search**: Native cosine similarity with `<=>` operator
- **JSON Support**: Native JSONB for structured data storage
- **Full-text Search**: Built-in text search capabilities
- **Connection Pooling**: Better resource management
- **Backup & Recovery**: Enterprise-grade data protection

## 📋 Prerequisites

### 1. Install PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS with Homebrew
brew install postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### 2. Install pgvector Extension
```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# macOS with Homebrew
brew install pgvector

# From source (if package not available)
git clone --branch v0.5.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 3. Install Python Dependencies
```bash
pip install psycopg2-binary pgvector
```

## 🔧 Database Setup

### 1. Create Database and User
```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database
CREATE DATABASE personalab;

-- Create user (optional, you can use existing user)
CREATE USER personalab_user WITH PASSWORD 'your_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE personalab TO personalab_user;

-- Exit PostgreSQL
\q
```

### 2. Enable pgvector Extension
```sql
-- Connect to your database
psql -d personalab -U personalab_user

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Exit
\q
```

## ⚙️ Configuration Methods

PersonaLab provides multiple ways to configure PostgreSQL:

### Method 1: Environment Variables (Recommended)
Create a `.env` file or set environment variables:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=personalab
POSTGRES_USER=personalab_user
POSTGRES_PASSWORD=your_password
```

### Method 2: Direct Configuration
```python
from personalab import setup_postgresql

# Setup PostgreSQL backend
db_manager = setup_postgresql(
    host='localhost',
    port='5432',
    dbname='personalab',
    user='personalab_user',
    password='your_password'
)
```

### Method 3: Connection String
```python
from personalab import setup_postgresql

# Using connection string
db_manager = setup_postgresql(
    connection_string='postgresql://user:password@localhost:5432/personalab'
)
```

## 🔄 Migration Process

### Automatic Migration (Recommended)
PersonaLab automatically detects PostgreSQL configuration and migrates:

```python
import os
from personalab import Persona, MemoryClient, ConversationManager

# Set environment variables
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_DB'] = 'personalab'
os.environ['POSTGRES_USER'] = 'personalab_user'
os.environ['POSTGRES_PASSWORD'] = 'your_password'

# Use PersonaLab normally - it will auto-detect PostgreSQL
persona = Persona(agent_id="my_agent")
response = persona.chat("Hello!", user_id="user123")
```

### Manual Migration
```python
from personalab import setup_postgresql, MemoryClient, ConversationManager

# Setup PostgreSQL
db_manager = setup_postgresql(
    host='localhost',
    dbname='personalab',
    user='personalab_user',
    password='your_password'
)

# Initialize components with PostgreSQL
memory_client = MemoryClient(db_manager=db_manager)
conversation_manager = ConversationManager(db_manager=db_manager)
```

### Migrating Existing Data
If you have existing SQLite data, you can migrate it:

```python
from personalab import setup_sqlite, setup_postgresql
from personalab.memory import MemoryClient

# Load from SQLite
sqlite_manager = setup_sqlite(
    memory_db_path="old_memory.db",
    conversation_db_path="old_conversations.db"
)
sqlite_memory = MemoryClient(db_manager=sqlite_manager)

# Setup PostgreSQL
pg_manager = setup_postgresql(host='localhost', dbname='personalab')
pg_memory = MemoryClient(db_manager=pg_manager)

# Export from SQLite and import to PostgreSQL
memory_data = sqlite_memory.export_memory("agent_id", "user_id")
pg_memory.import_memory(memory_data)
```

## 📊 Performance Comparison

| Feature | SQLite | PostgreSQL + pgvector |
|---------|--------|----------------------|
| Vector Search | Python cosine similarity | Native `<=>` operator |
| Concurrent Users | Limited | Unlimited |
| Index Type | Basic | HNSW (optimized) |
| Transaction Support | Basic | Full ACID |
| Memory Usage | High (Python vectors) | Low (native vectors) |
| Search Speed | O(n) | O(log n) with index |

## 🛠️ Advanced Configuration

### Vector Index Tuning
```sql
-- Create optimized HNSW index
CREATE INDEX conversation_vector_idx ON conversations 
USING hnsw (conversation_vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Create index for message vectors
CREATE INDEX message_vector_idx ON conversation_messages 
USING hnsw (message_vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

### Connection Pool Configuration
```python
from personalab import setup_postgresql

# Configure connection pooling
db_manager = setup_postgresql(
    host='localhost',
    dbname='personalab',
    user='personalab_user',
    password='your_password',
    # Additional psycopg2 connection parameters
    connect_timeout=10,
    keepalives_idle=600,
    keepalives_interval=30,
    keepalives_count=3
)
```

## 🔍 Monitoring and Maintenance

### Check Vector Index Usage
```sql
-- Check index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%vector%';

-- Check table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public';
```

### Performance Monitoring
```sql
-- Monitor slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements 
WHERE query LIKE '%vector%' 
ORDER BY mean_exec_time DESC;

-- Check vector operations
SELECT * FROM pg_stat_user_tables WHERE relname IN ('conversations', 'conversation_messages');
```

## 🐛 Troubleshooting

### Common Issues

1. **pgvector Extension Not Found**
   ```
   ERROR: extension "vector" is not available
   ```
   **Solution**: Install pgvector extension for your PostgreSQL version

2. **Connection Refused**
   ```
   psycopg2.OperationalError: could not connect to server
   ```
   **Solution**: Check if PostgreSQL is running and connection parameters are correct

3. **Permission Denied**
   ```
   psycopg2.errors.InsufficientPrivilege: permission denied
   ```
   **Solution**: Grant proper permissions to your user

4. **Vector Dimension Mismatch**
   ```
   ERROR: expected 1536 dimensions, not 384
   ```
   **Solution**: Ensure all vectors have the same dimension (1536 for OpenAI, 384 for sentence-transformers)

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from personalab import setup_postgresql
db_manager = setup_postgresql(host='localhost', dbname='personalab')

# Test connection
if db_manager.test_connection():
    print("✅ PostgreSQL connection successful!")
    print(f"Backend info: {db_manager.get_backend_info()}")
else:
    print("❌ Connection failed!")
```

## 📚 Example Usage

See `examples/postgresql_example.py` for a complete working example:

```bash
cd examples
python postgresql_example.py
```

## 🔄 Rollback to SQLite

If you need to rollback to SQLite:

```python
from personalab import setup_sqlite

# Configure SQLite backend
db_manager = setup_sqlite(
    memory_db_path="memory.db",
    conversation_db_path="conversations.db"
)

# Use with PersonaLab components
from personalab import Persona
persona = Persona(agent_id="my_agent", db_manager=db_manager)
```

## 🚀 Production Deployment

### Docker Configuration
```dockerfile
FROM python:3.9

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Your application code
COPY . /app
WORKDIR /app

ENV POSTGRES_HOST=db
ENV POSTGRES_DB=personalab
ENV POSTGRES_USER=personalab_user
ENV POSTGRES_PASSWORD=secure_password

CMD ["python", "your_app.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: personalab
      POSTGRES_USER: personalab_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  app:
    build: .
    depends_on:
      - db
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: personalab
      POSTGRES_USER: personalab_user
      POSTGRES_PASSWORD: secure_password

volumes:
  postgres_data:
```

## 📈 Next Steps

1. **Monitor Performance**: Set up monitoring for your PostgreSQL instance
2. **Backup Strategy**: Implement regular backups using `pg_dump`
3. **Scaling**: Consider read replicas for high-traffic applications
4. **Security**: Use SSL connections and proper authentication
5. **Optimization**: Tune PostgreSQL configuration for your workload

For more advanced configurations and enterprise features, consult the PostgreSQL and pgvector documentation. 