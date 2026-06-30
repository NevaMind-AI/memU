# Milvus Vector Index

memU can route in-memory metadata-store similarity search to [Milvus](https://milvus.io/) as an external vector index. This is useful when:

- **Scale**: you have more vectors than the brute-force fallback can handle at latency budget.
- **Managed deployments**: you want to offload vector infrastructure to Zilliz Cloud or a self-hosted Milvus cluster.
- **Zero-setup local dev**: Milvus Lite runs as a local file (`./milvus.db`) with no external service.

## Install

```bash
uv sync --extra milvus
```

> The `milvus` extra pulls `pymilvus`, `milvus-lite` and — on Python 3.13 — a `setuptools<81` pin to work around [milvus-lite's use of the removed `pkg_resources` API](https://github.com/milvus-io/milvus-lite/issues).

## Quick Start (Milvus Lite)

```python
from memu.app import MemoryService

service = MemoryService(
    llm_profiles={"default": {"api_key": "your-api-key"}},
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

memU keeps metadata records (summary, categories, scope, reinforcement stats, ...) in the metadata store and mirrors embeddings into Milvus on create / update / delete.

- **Available now**: `inmemory` metadata store + Milvus vector index (feature-complete).
- **Not wired yet**: `sqlite` and `postgres` metadata stores reject `vector_index.provider="milvus"` rather than silently ignoring it. See `docs/adr/0006-external-vector-index.md` for the rollout plan.

## How Search Works

1. `create_item` / `update_item` mirror the embedding (and scope fields such as `user_id`, `agent_id`) into the configured Milvus collection.
2. `vector_search_items` forwards the query vector to Milvus using a COSINE AUTOINDEX. Scope filters (e.g. `where={"user_id": "u1"}`) are translated into Milvus boolean expressions on dynamic fields.
3. Milvus returns `(id, score)` pairs; the metadata store resolves them back to full memory records.
4. Salience ranking (`ranking="salience"`) still runs locally because it needs per-item reinforcement and recency factors that the vector index does not store.
