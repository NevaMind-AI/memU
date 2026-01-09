# MemU Tests

This directory contains the test suite for the MemU memory framework.

## Prerequisites

### 1. Install Test Dependencies

```bash
uv sync --group test
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY=your_openai_api_key
```

For PostgreSQL tests, optionally set:

```bash
export POSTGRES_DSN=postgresql+psycopg://postgres:postgres@localhost:5432/memu
```

### 3. Start PostgreSQL (for postgres tests only)

```bash
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Files

```bash
# In-memory storage tests only
pytest tests/test_inmemory.py -v

# PostgreSQL storage tests only
pytest tests/test_postgres.py -v
```

### Using Markers

The test suite uses markers to categorize tests:

| Marker | Description |
|--------|-------------|
| `slow` | Tests that involve LLM API calls (slower execution) |
| `integration` | Integration tests requiring external services |
| `postgres` | Tests that require a PostgreSQL database |

#### Skip Slow Tests

```bash
pytest tests/ -v -m "not slow"
```

#### Skip PostgreSQL Tests

```bash
pytest tests/ -v -m "not postgres"
```

#### Skip All Integration Tests

```bash
pytest tests/ -v -m "not integration"
```

#### Combine Markers

```bash
# Run only fast, non-postgres tests
pytest tests/ -v -m "not slow and not postgres"
```

## Test Coverage

Generate a coverage report:

```bash
pytest tests/ -v --cov=memu --cov-report=term-missing
```

Generate HTML coverage report:

```bash
pytest tests/ -v --cov=memu --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── example/
│   └── example_conversation.json  # Test data
├── test_inmemory.py         # In-memory storage backend tests
├── test_postgres.py         # PostgreSQL storage backend tests
└── README.md                # This file
```

## Writing New Tests

### Basic Test Structure

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
class TestNewFeature:
    """Tests for the new feature."""

    @pytest.mark.asyncio
    async def test_feature_works(self, inmemory_service):
        """Test that the feature works correctly."""
        result = await inmemory_service.some_method()
        assert result is not None
```

### Available Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `openai_api_key` | session | OpenAI API key from environment |
| `postgres_dsn` | session | PostgreSQL connection string |
| `example_conversation_path` | session | Path to example conversation JSON |
| `inmemory_service` | function | MemoryService with in-memory backend |
| `postgres_service` | function | MemoryService with PostgreSQL backend |
| `sample_queries` | function | Sample query list for retrieval tests |

### Skipping Tests

Tests are automatically skipped when:
- `OPENAI_API_KEY` is not set
- PostgreSQL is not available (for postgres tests)

You can also manually skip:

```python
@pytest.mark.skipif(condition, reason="Reason for skipping")
async def test_conditional():
    pass
```

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

Set the environment variable before running tests:

```bash
export OPENAI_API_KEY=sk-xxx
pytest tests/ -v
```

### "PostgreSQL not available"

1. Ensure Docker is running
2. Start the PostgreSQL container (see Prerequisites)
3. Wait a few seconds for the database to initialize

### Rate Limiting

If you encounter OpenAI rate limits, run fewer tests at a time:

```bash
# Run one test file at a time
pytest tests/test_inmemory.py -v

# Or run with fewer parallel workers
pytest tests/ -v -n 1
```

