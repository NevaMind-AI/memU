# Milvus Vector Index

memU can route in-memory metadata-store similarity search to [Milvus](https://milvus.io/) as an external vector index. This is useful when:

- **Scale**: you have more vectors than the brute-force fallback can handle at latency budget.
- **Managed deployments**: you want to offload vector infrastructure to Zilliz Cloud or a self-hosted Milvus cluster.
- **Zero-setup local dev**: Milvus Lite runs as a local file (`./milvus.db`) with no external service.

## Install

```bash
uv sync --extra milvus
```

> The `milvus` extra uses Milvus Lite 3.1.1 or newer. This excludes the known 3.0 score and dynamic-field compatibility window and starts with the first 3.1 patch release. New local databases use the 3.x storage format; older 2.x `.db` files are not reusable and must be rebuilt from the metadata source.

## Quick Start (Milvus Lite)

```python
from memu.app import MemoryService

service = MemoryService(
    embedding_profiles={"default": {"api_key": "your-api-key"}},
    database_config={
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {"provider": "milvus"},
    },
)
```

With the default configuration the index is stored in `./milvus.db` using Milvus Lite — no Docker or separate process. The accompanying `inmemory` metadata is process-local and remains the source used to materialize search hits.

## Targeting a Milvus Server

```python
database_config = {
    "metadata_store": {"provider": "inmemory"},
    "vector_index": {
        "provider": "milvus",
        "uri": "http://localhost:19530",
        "collection_name": "memu_prod",
    },
}
```

## Targeting Zilliz Cloud

```python
import os

database_config = {
    "metadata_store": {"provider": "inmemory"},
    "vector_index": {
        "provider": "milvus",
        "uri": os.environ["ZILLIZ_URI"],
        "token": os.environ["ZILLIZ_TOKEN"],
        "collection_name": "memu_prod",
    },
}
```

## Configuration

| Field | Default | Notes |
| --- | --- | --- |
| `provider` | — | Must be `"milvus"` to enable this index. |
| `uri` | `"./milvus.db"` | File path runs Milvus Lite; `http(s)://host:port` targets a Milvus server; a Zilliz Cloud endpoint targets the managed service. |
| `token` | `None` | Auth token for Zilliz Cloud or a secured Milvus server. |
| `db_name` | `None` | Optional Milvus database name. |
| `collection_name` | `"memu_memory_items"` | Name of the Milvus collection that holds memory vectors. |
| `dim` | `None` | Embedding dimension. Inferred from the first upsert when omitted. |
| `consistency_level` | `None` | Optional Milvus collection consistency level (`"Strong"`, `"Session"`, `"Bounded"`, or `"Eventually"`). Uses the server default when omitted. |

## Supported Combinations

memU keeps recall files, resources, segment text, and scope fields in the metadata store and mirrors only `RecallFileSegment` embeddings into Milvus. Resource retrieval stays in the metadata backend.

- **Available now**: `inmemory` metadata store + Milvus vector index for segment retrieval.
- **Not wired yet**: `sqlite` and `postgres` metadata stores reject `vector_index.provider="milvus"` rather than silently ignoring it. See `docs/adr/0019-external-vector-index.md` for the rollout plan.

Each `InMemoryStore` receives a private internal scope inside the shared Milvus collection. Two live stores can therefore use the same collection without seeing or consuming each other's top-k results. A normal `close()` deletes only the segment IDs owned by that store and never drops the collection.

Because metadata is intentionally ephemeral, a new process starts with a new internal scope and does not recover vectors written by an earlier process. If a process exits without calling `close()`, its vectors may remain in the collection but are unreachable from later stores. Applications that need restart recovery should use a persistent metadata backend; Milvus is currently rejected for those backend combinations rather than presenting an incomplete recovery model.

## How Search Works

1. `commit_results` creates or reconciles `RecallFileSegment` rows and mirrors each segment embedding plus scope fields such as `user_id`, `agent_id`, `track`, and `recall_file_id` into the configured Milvus collection.
2. `progressive_retrieve` forwards the query vector to Milvus through `recall_file_segment_repo.vector_search_segments` using a COSINE AUTOINDEX. Scope filters (e.g. `where={"user_id": "u1"}`) and track filters are translated into Milvus boolean expressions on dynamic fields.
3. Milvus returns `(segment_id, score)` pairs; the metadata store resolves them back to segment records and rolls them up to recall files.
4. Resource retrieval stays in the metadata backend because Milvus is only wired to the segment index in the first rollout.

When reusing a collection, memU validates the string primary key, float-vector field, dimension, dynamic-field support, and COSINE index before writing. An incompatible collection fails with a descriptive error and is never modified.
