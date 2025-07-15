# MemU PostgreSQL Configuration Guide

## Problem Resolution ✅

MemU is configured to use PostgreSQL database for production-ready deployment.

## Root Cause Analysis

MemU's database selection logic is located in `memu/config/database.py`:

```python
@classmethod
def from_env(cls) -> "DatabaseConfig":
    # Check PostgreSQL environment variables
    postgres_host = os.getenv('POSTGRES_HOST')
    postgres_db = os.getenv('POSTGRES_DB')
    
    # If PostgreSQL environment variables are set, use PostgreSQL
    if postgres_host and postgres_db:
        return cls(backend="postgresql", ...)
    
    # Otherwise use default settings
    return cls(backend="postgresql", ...)
```

**Key Point**: The system will only use PostgreSQL when both `POSTGRES_HOST` and `POSTGRES_DB` environment variables are set.

## Current Configuration ✅

### Environment Variable Setup
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=memu
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""
```

### Verification Status
- ✅ Database backend: PostgreSQL
- ✅ Database connection: Successful
- ✅ Database setup: Completed

## Quick Usage

### Method 1: Manual Environment Variable Setup Each Time
```bash
# Set environment variables
source setup_postgres_env.sh

# Use MemU
python your_script.py
```

### Method 2: Permanent Configuration (Recommended)
Add environment variables to your `~/.zshrc` file:

```bash
# Add to the end of ~/.zshrc file
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=memu
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""

# Reload configuration
source ~/.zshrc
```

## Configuration Tools

### Automatic Configuration Script
```bash
# Run complete configuration and testing
python configure_postgresql.py
```

### Verify Configuration
```bash
# Verify current configuration status
python test_postgres_config.py
```

### Environment Setup Script
```bash
# Quick environment variable setup (needs to be run each time)
source setup_postgres_env.sh
```

## PostgreSQL Service Management

### Start PostgreSQL Service
```bash
brew services start postgresql@14
```

### Stop PostgreSQL Service
```bash
brew services stop postgresql@14
```

### Check Service Status
```bash
brew services list | grep postgres
```

## Database Management

### Connect to Database
```bash
psql -d memu
```

### View Table Structure
```sql
-- Memory-related tables
\dt memory*

-- Conversation-related tables  
\dt conversation*
```

### Backup Database
```bash
pg_dump memu > memu_backup.sql
```

## Troubleshooting

### 1. PostgreSQL Service Not Running
```bash
# Start service
brew services start postgresql@14

# Verify status
brew services list | grep postgres
```

### 2. Connection Permission Issues
```bash
# Ensure user has permission to access database
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE memu TO chenhong;"
```

### 3. Environment Variables Not Set
```bash
# Check environment variables
env | grep POSTGRES

# Reset
source setup_postgres_env.sh
```

### 4. Database Connection Issues
- Confirm environment variables are set correctly: `echo $POSTGRES_HOST`
- Restart Python process
- Run verification script: `python test_postgres_config.py`

## PostgreSQL Advantages

PostgreSQL provides enterprise-grade features:

1. **Performance**: Excellent concurrency and query optimization
2. **Scalability**: Support for large datasets and high user counts
3. **Features**: Support for vector search (pgvector extension)
4. **Production Ready**: Robust, reliable database for production deployments
5. **Backup and Recovery**: Comprehensive backup and recovery mechanisms

## Summary

MemU is configured to use PostgreSQL database for optimal performance and scalability. Simply ensure the correct environment variables are set before use. 