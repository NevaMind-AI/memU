# memU Service API Reference

This document provides a comprehensive reference for the `MemoryService` class, the primary interface for interacting with the memU memory system.

## Table of Contents

- [Overview](#overview)
- [Initialization](#initialization)
- [Core Methods](#core-methods)
  - [memorize](#memorize)
  - [retrieve](#retrieve)
- [CRUD Operations](#crud-operations)
  - [create_memory_item](#create_memory_item)
  - [update_memory_item](#update_memory_item)
  - [delete_memory_item](#delete_memory_item)
  - [list_memory_items](#list_memory_items)
  - [list_memory_categories](#list_memory_categories)
- [Pipeline Configuration](#pipeline-configuration)
  - [configure_pipeline](#configure_pipeline)
  - [insert_step_after](#insert_step_after)
  - [insert_step_before](#insert_step_before)
  - [replace_step](#replace_step)
  - [remove_step](#remove_step)
- [Configuration Types](#configuration-types)

---

## Overview

`MemoryService` is the main entry point for the memU memory system. It provides methods to:

- **Memorize**: Extract and store structured memories from various resource types (conversations, documents, images, videos, audio)
- **Retrieve**: Query and retrieve relevant memories using RAG or LLM-based ranking
- **CRUD**: Create, read, update, and delete individual memory items
- **Pipeline Customization**: Extend and modify the internal processing pipelines

---

## Initialization

```python
from memu import MemoryService

service = MemoryService(
    llm_profiles=...,
    blob_config=...,
    database_config=...,
    memorize_config=...,
    retrieve_config=...,
    workflow_runner=...,
    user_config=...,
)
```

### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `llm_profiles` | `LLMProfilesConfig \| dict \| None` | Configuration for LLM backends. Supports multiple named profiles. |
| `blob_config` | `BlobConfig \| dict \| None` | Configuration for resource storage (local filesystem). |
| `database_config` | `DatabaseConfig \| dict \| None` | Configuration for metadata store and vector index. |
| `memorize_config` | `MemorizeConfig \| dict \| None` | Configuration for memory extraction behavior. |
| `retrieve_config` | `RetrieveConfig \| dict \| None` | Configuration for retrieval behavior. |
| `workflow_runner` | `WorkflowRunner \| str \| None` | Workflow execution backend (default: sequential runner). |
| `user_config` | `UserConfig \| dict \| None` | Configuration for user scope model. |

---

## Core Methods

### memorize

Extract and store structured memories from a resource.

```python
async def memorize(
    self,
    *,
    resource_url: str,
    modality: str,
    summary_prompt: str | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource_url` | `str` | Yes | URL or local path to the resource to process. |
| `modality` | `str` | Yes | Type of resource: `"conversation"`, `"document"`, `"image"`, `"video"`, or `"audio"`. |
| `summary_prompt` | `str \| None` | No | Optional custom prompt for summarization. |
| `user` | `dict[str, Any] \| None` | No | User scope data for multi-tenancy (e.g., `{"user_id": "u123"}`). |

#### Returns

```python
{
    "resource": {
        "id": str,
        "url": str,
        "modality": str,
        "local_path": str,
        "caption": str | None,
        "created_at": str,
        "updated_at": str,
        # ... user scope fields
    },
    "items": [
        {
            "id": str,
            "resource_id": str,
            "memory_type": str,  # "profile", "event", "knowledge", "behavior"
            "summary": str,
            "created_at": str,
            "updated_at": str,
            # ... user scope fields
        },
        ...
    ],
    "categories": [
        {
            "id": str,
            "name": str,
            "description": str,
            "summary": str | None,
            # ... user scope fields
        },
        ...
    ],
    "relations": [
        {
            "item_id": str,
            "category_id": str,
            # ... user scope fields
        },
        ...
    ]
}
```

#### Example

```python
result = await service.memorize(
    resource_url="./conversations/chat_001.json",
    modality="conversation",
    user={"user_id": "alice"},
)

print(f"Extracted {len(result['items'])} memory items")
for item in result["items"]:
    print(f"  [{item['memory_type']}] {item['summary'][:80]}...")
```

---

### retrieve

Query and retrieve relevant memories.

```python
async def retrieve(
    self,
    queries: list[dict[str, Any]],
    where: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `queries` | `list[dict[str, Any]]` | Yes | List of query messages. The last message is the active query; earlier messages provide conversation context. |
| `where` | `dict[str, Any] \| None` | No | Filter conditions for user scope (e.g., `{"user_id": "u123"}`). |

#### Query Message Format

```python
{
    "role": "user" | "assistant",
    "content": {
        "text": str  # The query text
    }
}
# Or simplified:
{
    "role": "user",
    "content": str  # Direct text content
}
```

#### Returns

```python
{
    "needs_retrieval": bool,  # Whether retrieval was actually performed
    "original_query": str,    # The original query text
    "rewritten_query": str,   # Query rewritten with context
    "next_step_query": str | None,  # Suggested follow-up query
    "categories": [
        {
            "id": str,
            "name": str,
            "summary": str,
            "score": float,  # Relevance score (RAG mode only)
            ...
        },
        ...
    ],
    "items": [
        {
            "id": str,
            "memory_type": str,
            "summary": str,
            "score": float,  # Relevance score (RAG mode only)
            ...
        },
        ...
    ],
    "resources": [
        {
            "id": str,
            "url": str,
            "caption": str,
            "score": float,  # Relevance score (RAG mode only)
            ...
        },
        ...
    ]
}
```

#### Example

```python
# Simple single query
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "What hobbies does the user enjoy?"}}
    ],
    where={"user_id": "alice"},
)

# With conversation context
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "Tell me about yourself"}},
        {"role": "assistant", "content": {"text": "I'd be happy to help..."}},
        {"role": "user", "content": {"text": "What are my favorite foods?"}},
    ],
    where={"user_id": "alice"},
)

print(f"Found {len(result['items'])} relevant memories")
for item in result["items"]:
    print(f"  - {item['summary']}")
```

---

## CRUD Operations

### create_memory_item

Create a new memory item directly.

```python
async def create_memory_item(
    self,
    *,
    memory_type: MemoryType,
    memory_content: str,
    memory_categories: list[str],
    user: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `memory_type` | `MemoryType` | Yes | Type: `"profile"`, `"event"`, `"knowledge"`, or `"behavior"`. |
| `memory_content` | `str` | Yes | The memory content/summary text. |
| `memory_categories` | `list[str]` | Yes | List of category names to associate with. |
| `user` | `dict[str, Any] \| None` | No | User scope data. |

#### Returns

```python
{
    "memory_item": {
        "id": str,
        "memory_type": str,
        "summary": str,
        ...
    },
    "category_updates": [
        {
            "id": str,
            "name": str,
            "summary": str,  # Updated summary
            ...
        },
        ...
    ]
}
```

#### Example

```python
result = await service.create_memory_item(
    memory_type="profile",
    memory_content="The user works as a software engineer at Acme Corp",
    memory_categories=["work_life", "personal_info"],
    user={"user_id": "alice"},
)
print(f"Created memory: {result['memory_item']['id']}")
```

---

### update_memory_item

Update an existing memory item.

```python
async def update_memory_item(
    self,
    *,
    memory_id: str,
    memory_type: MemoryType | None = None,
    memory_content: str | None = None,
    memory_categories: list[str] | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `memory_id` | `str` | Yes | ID of the memory item to update. |
| `memory_type` | `MemoryType \| None` | No | New memory type (if changing). |
| `memory_content` | `str \| None` | No | New content/summary (if changing). |
| `memory_categories` | `list[str] \| None` | No | New category associations (replaces existing). |
| `user` | `dict[str, Any] \| None` | No | User scope data. |

> **Note**: At least one of `memory_type`, `memory_content`, or `memory_categories` must be provided.

#### Returns

Same structure as `create_memory_item`.

#### Example

```python
result = await service.update_memory_item(
    memory_id="mem_abc123",
    memory_content="The user now works as a senior software engineer",
    memory_categories=["work_life"],
    user={"user_id": "alice"},
)
```

---

### delete_memory_item

Delete a memory item.

```python
async def delete_memory_item(
    self,
    *,
    memory_id: str,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `memory_id` | `str` | Yes | ID of the memory item to delete. |
| `user` | `dict[str, Any] \| None` | No | User scope data. |

#### Returns

Same structure as `create_memory_item`, with the deleted item data.

#### Example

```python
result = await service.delete_memory_item(
    memory_id="mem_abc123",
    user={"user_id": "alice"},
)
print(f"Deleted: {result['memory_item']['summary']}")
```

---

### list_memory_items

List all memory items, optionally filtered.

```python
async def list_memory_items(
    self,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `where` | `dict[str, Any] \| None` | No | Filter conditions for user scope. |

#### Returns

```python
{
    "items": [
        {
            "id": str,
            "resource_id": str | None,
            "memory_type": str,
            "summary": str,
            "created_at": str,
            "updated_at": str,
            ...
        },
        ...
    ]
}
```

#### Example

```python
result = await service.list_memory_items(
    where={"user_id": "alice"}
)
print(f"Total memories: {len(result['items'])}")
```

---

### list_memory_categories

List all memory categories, optionally filtered.

```python
async def list_memory_categories(
    self,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `where` | `dict[str, Any] \| None` | No | Filter conditions for user scope. |

#### Returns

```python
{
    "categories": [
        {
            "id": str,
            "name": str,
            "description": str,
            "summary": str | None,
            "created_at": str,
            "updated_at": str,
            ...
        },
        ...
    ]
}
```

#### Example

```python
result = await service.list_memory_categories(
    where={"user_id": "alice"}
)
for cat in result["categories"]:
    print(f"{cat['name']}: {cat['summary'][:50] if cat['summary'] else 'No summary'}...")
```

---

## Pipeline Configuration

The `MemoryService` uses configurable workflows (pipelines) for processing. You can modify these pipelines at runtime.

### Available Pipelines

| Pipeline Name | Description |
|---------------|-------------|
| `memorize` | Memory extraction workflow |
| `retrieve_rag` | RAG-based retrieval workflow |
| `retrieve_llm` | LLM-based retrieval workflow |
| `patch_create` | Create memory item workflow |
| `patch_update` | Update memory item workflow |
| `patch_delete` | Delete memory item workflow |
| `crud_list_memory_items` | List memory items workflow |
| `crud_list_memory_categories` | List memory categories workflow |

---

### configure_pipeline

Configure a specific step in a pipeline.

```python
def configure_pipeline(
    self,
    *,
    step_id: str,
    configs: Mapping[str, Any],
    pipeline: str = "memorize",
) -> int
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `step_id` | `str` | Yes | ID of the step to configure. |
| `configs` | `Mapping[str, Any]` | Yes | Configuration key-value pairs. |
| `pipeline` | `str` | No | Pipeline name (default: `"memorize"`). |

#### Returns

`int`: New revision number of the pipeline.

#### Example

```python
# Configure the extraction step to use a different LLM profile
revision = service.configure_pipeline(
    step_id="extract_items",
    configs={"llm_profile": "gpt4"},
    pipeline="memorize",
)
```

---

### insert_step_after

Insert a new step after an existing step.

```python
def insert_step_after(
    self,
    *,
    target_step_id: str,
    new_step: WorkflowStep,
    pipeline: str = "memorize",
) -> int
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_step_id` | `str` | Yes | ID of the step to insert after. |
| `new_step` | `WorkflowStep` | Yes | The new workflow step to insert. |
| `pipeline` | `str` | No | Pipeline name (default: `"memorize"`). |

#### Returns

`int`: New revision number of the pipeline.

#### Example

```python
from memu.workflow.step import WorkflowStep

async def custom_filter(state, context):
    # Filter out short memories
    items = state.get("items", [])
    state["items"] = [i for i in items if len(i.summary) > 20]
    return state

new_step = WorkflowStep(
    step_id="filter_short_items",
    role="filter",
    handler=custom_filter,
    requires={"items"},
    produces={"items"},
    capabilities=set(),
)

revision = service.insert_step_after(
    target_step_id="extract_items",
    new_step=new_step,
    pipeline="memorize",
)
```

---

### insert_step_before

Insert a new step before an existing step.

```python
def insert_step_before(
    self,
    *,
    target_step_id: str,
    new_step: WorkflowStep,
    pipeline: str = "memorize",
) -> int
```

#### Parameters

Same as `insert_step_after`.

---

### replace_step

Replace an existing step with a new one.

```python
def replace_step(
    self,
    *,
    target_step_id: str,
    new_step: WorkflowStep,
    pipeline: str = "memorize",
) -> int
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_step_id` | `str` | Yes | ID of the step to replace. |
| `new_step` | `WorkflowStep` | Yes | The replacement workflow step. |
| `pipeline` | `str` | No | Pipeline name (default: `"memorize"`). |

#### Returns

`int`: New revision number of the pipeline.

---

### remove_step

Remove a step from the pipeline.

```python
def remove_step(
    self,
    *,
    target_step_id: str,
    pipeline: str = "memorize",
) -> int
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_step_id` | `str` | Yes | ID of the step to remove. |
| `pipeline` | `str` | No | Pipeline name (default: `"memorize"`). |

#### Returns

`int`: New revision number of the pipeline.

---

## Configuration Types

### LLMConfig

Configuration for an LLM backend.

```python
class LLMConfig(BaseModel):
    provider: str = "openai"           # LLM provider identifier
    base_url: str = "https://api.openai.com/v1"
    api_key: str = "OPENAI_API_KEY"
    chat_model: str = "gpt-4o-mini"
    client_backend: str = "sdk"        # "sdk" or "httpx"
    endpoint_overrides: dict[str, str] = {}
    embed_model: str = "text-embedding-3-small"
    embed_batch_size: int = 25
```

### LLMProfilesConfig

Container for multiple LLM profiles.

```python
# Usage example
llm_profiles = {
    "default": {
        "chat_model": "gpt-4o-mini",
        "api_key": "sk-...",
    },
    "gpt4": {
        "chat_model": "gpt-4o",
        "api_key": "sk-...",
    },
    "local": {
        "base_url": "http://localhost:11434/v1",
        "chat_model": "llama3",
    },
}
```

### DatabaseConfig

Configuration for storage backends.

```python
class DatabaseConfig(BaseModel):
    metadata_store: MetadataStoreConfig
    vector_index: VectorIndexConfig | None

class MetadataStoreConfig(BaseModel):
    provider: Literal["inmemory", "postgres"] = "inmemory"
    ddl_mode: Literal["create", "validate"] = "create"
    dsn: str | None = None  # Required for postgres

class VectorIndexConfig(BaseModel):
    provider: Literal["bruteforce", "pgvector", "none"] = "bruteforce"
    dsn: str | None = None  # Required for pgvector
```

### MemorizeConfig

Configuration for memory extraction.

```python
class MemorizeConfig(BaseModel):
    category_assign_threshold: float = 0.25
    multimodal_preprocess_prompts: dict[str, str | CustomPrompt] = {}
    preprocess_llm_profile: str = "default"
    memory_types: list[str] = ["profile", "event", "knowledge", "behavior"]
    memory_type_prompts: dict[str, str | CustomPrompt] = {...}
    memory_extract_llm_profile: str = "default"
    memory_categories: list[CategoryConfig] = [...]  # Default 10 categories
    default_category_summary_prompt: str | CustomPrompt = ...
    default_category_summary_target_length: int = 400
    category_update_llm_profile: str = "default"
```

### RetrieveConfig

Configuration for retrieval behavior.

```python
class RetrieveConfig(BaseModel):
    method: Literal["rag", "llm"] = "rag"
    route_intention: bool = True
    category: RetrieveCategoryConfig  # enabled, top_k
    item: RetrieveItemConfig          # enabled, top_k
    resource: RetrieveResourceConfig  # enabled, top_k
    sufficiency_check: bool = True
    sufficiency_check_prompt: str = ""
    sufficiency_check_llm_profile: str = "default"
    llm_ranking_llm_profile: str = "default"
```

### CategoryConfig

Configuration for a memory category.

```python
class CategoryConfig(BaseModel):
    name: str                          # Category name (required)
    description: str = ""              # Category description
    target_length: int | None = None   # Target summary length
    summary_prompt: str | CustomPrompt | None = None
```

### UserConfig

Configuration for user scope model.

```python
class UserConfig(BaseModel):
    model: type[BaseModel] = DefaultUserModel

class DefaultUserModel(BaseModel):
    user_id: str | None = None
```

You can define a custom user model for multi-tenancy:

```python
from pydantic import BaseModel

class MyUserModel(BaseModel):
    user_id: str
    tenant_id: str
    region: str | None = None

service = MemoryService(
    user_config={"model": MyUserModel},
    ...
)
```

---

## Memory Types

The system supports four built-in memory types:

| Type | Description |
|------|-------------|
| `profile` | Personal information, traits, characteristics |
| `event` | Events, activities, experiences |
| `knowledge` | Facts, learned information, skills |
| `behavior` | Habits, patterns, preferences |

---

## Default Categories

The default memory categories are:

| Category | Description |
|----------|-------------|
| `personal_info` | Personal information about the user |
| `preferences` | User preferences, likes and dislikes |
| `relationships` | Information about relationships with others |
| `activities` | Activities, hobbies, and interests |
| `goals` | Goals, aspirations, and objectives |
| `experiences` | Past experiences and events |
| `knowledge` | Knowledge, facts, and learned information |
| `opinions` | Opinions, viewpoints, and perspectives |
| `habits` | Habits, routines, and patterns |
| `work_life` | Work-related information and professional life |

---

## Supported Modalities

| Modality | Description | Preprocessing |
|----------|-------------|---------------|
| `conversation` | Chat/dialogue data (JSON format) | Segmentation, summarization |
| `document` | Text documents | Content extraction, summarization |
| `image` | Image files | Vision API analysis |
| `video` | Video files | Frame extraction + Vision API |
| `audio` | Audio files | Transcription + text processing |

---

## Error Handling

The service raises standard Python exceptions:

| Exception | Condition |
|-----------|-----------|
| `ValueError` | Invalid parameters (e.g., unknown memory type, empty queries) |
| `KeyError` | Unknown LLM profile name |
| `RuntimeError` | Workflow execution failure |
| `TypeError` | Invalid query message format |

Example:

```python
try:
    result = await service.retrieve(queries=[])
except ValueError as e:
    print(f"Invalid query: {e}")
```
