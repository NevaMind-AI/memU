# Milvus Vector Index

memU can route in-memory metadata-store similarity search to [Milvus](https://milvus.io/) as an external vector index. This is useful when:

- **Scale**: you have more vectors than the brute-force fallback can handle at latency budget.
- **Managed deployments**: you want to offload vector infrastructure to Zilliz Cloud or a self-hosted Milvus cluster.
- **Zero-setup local dev**: Milvus Lite runs as a local file (`./milvus.db`) with no external service.

## Install

```bash
uv sync --extra milvus
```

> The `milvus` extra pulls `pymilvus`, `milvus-lite` and — on Python 3.13 — a `setuptools<81` compatibility pin because Milvus Lite 3.0 still imports `pkg_resources`. New local Milvus Lite files should use the 3.x storage format; older 2.x `.db` files are not expected to be reusable after upgrading to Milvus Lite 3.x.

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

With the default configuration the index is persisted to `./milvus.db` using Milvus Lite — no Docker, no separate process.

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

memU keeps recall files, resources, segment text, and scope fields in the metadata store and mirrors `RecallFileSegment` embeddings into Milvus on create / delete.

- **Available now**: `inmemory` metadata store + Milvus vector index (feature-complete).
- **Not wired yet**: `sqlite` and `postgres` metadata stores reject `vector_index.provider="milvus"` rather than silently ignoring it. See `docs/adr/0012-external-vector-index.md` for the rollout plan.

## How Search Works

1. `commit_results` creates or reconciles `RecallFileSegment` rows and mirrors each segment embedding plus scope fields such as `user_id`, `agent_id`, `track`, and `recall_file_id` into the configured Milvus collection.
2. `progressive_retrieve` forwards the query vector to Milvus through `recall_file_segment_repo.vector_search_segments` using a COSINE AUTOINDEX. Scope filters (e.g. `where={"user_id": "u1"}`) and track filters are translated into Milvus boolean expressions on dynamic fields.
3. Milvus returns `(segment_id, score)` pairs; the metadata store resolves them back to segment records and rolls them up to recall files.
4. Resource retrieval stays in the metadata backend because Milvus is only wired to the segment index in the first rollout.
