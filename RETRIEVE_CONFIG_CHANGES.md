# Retrieve Config Changes

## Summary

Replaced the confusing `embedding_search` boolean parameter with a clearer `retrieve_config` configuration object.

## Changes Made

### 1. New Config Model (`src/memu/app/settings.py`)

Added `RetrieveConfig` class:

```python
class RetrieveConfig(BaseModel):
    method: str = Field(
        default="rag",
        description="Retrieval method: 'rag' for embedding-based vector search, 'llm' for LLM-based ranking.",
    )
    top_k: int = Field(
        default=5,
        description="Maximum number of results to return per category.",
    )
```

### 2. Updated Retrieve Method (`src/memu/app/service.py`)

**Before:**
```python
async def retrieve(
    self,
    query: str,
    *,
    top_k: int = 5,
    embedding_search: bool = True,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
```

**After:**
```python
async def retrieve(
    self,
    query: str,
    *,
    retrieve_config: dict[str, Any] | RetrieveConfig | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
```

### 3. Usage Examples

**Old API (confusing):**
```python
# RAG-based retrieval
result = await service.retrieve(query="...", embedding_search=True)  # True = use embeddings
result = await service.retrieve(query="...", embedding_search=False)  # False = use LLM (confusing!)
```

**New API (clear):**
```python
# RAG-based retrieval (default)
result = await service.retrieve(query="...")
result = await service.retrieve(query="...", retrieve_config={"method": "rag"})

# LLM-based retrieval
result = await service.retrieve(query="...", retrieve_config={"method": "llm"})

# Custom top_k
result = await service.retrieve(query="...", retrieve_config={"method": "rag", "top_k": 10})
```

## Benefits

1. **Clearer Intent**: `method="rag"` vs `method="llm"` is self-explanatory
2. **No Confusion**: `embedding_search=False` sounded like "don't search embeddings" but actually meant "use LLM"
3. **Extensible**: Easy to add more retrieval methods or config options in the future
4. **Type Safe**: Pydantic validation ensures correct parameters
5. **Better Defaults**: All config in one place with clear defaults

## Migration Guide

### Old Code
```python
# RAG-based
await service.retrieve(query="...", top_k=5, embedding_search=True)

# LLM-based
await service.retrieve(query="...", top_k=5, embedding_search=False)
```

### New Code
```python
# RAG-based
await service.retrieve(query="...", retrieve_config={"method": "rag", "top_k": 5})

# LLM-based
await service.retrieve(query="...", retrieve_config={"method": "llm", "top_k": 5})

# Or with default config (rag, top_k=5)
await service.retrieve(query="...")
```

## Files Modified

1. `src/memu/app/settings.py` - Added `RetrieveConfig` model
2. `src/memu/app/service.py` - Updated `retrieve` method signature and implementation
3. `src/memu/app/__init__.py` - Exported `RetrieveConfig`
4. `data/test.py` - Updated test examples
5. `data/retrieve_example.py` - Created new usage examples

## Additional Fixes

Fixed pre-existing syntax errors in `service.py`:
- Line 702: `except json.JSONDecodeError, TypeError:` → `except (json.JSONDecodeError, TypeError):`
- Line 718: `except TypeError, ValueError:` → `except (TypeError, ValueError):`
