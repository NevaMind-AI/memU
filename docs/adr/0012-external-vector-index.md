# ADR 0012: External Vector Index Alongside Metadata Store

- Status: Accepted
- Date: 2026-06-30

## Context

ADR 0002 locked in repository-based storage with backend-aware vector search. ADR 0007 then made `RecallFileSegment` the primary embedded retrieval unit: the `inmemory` and `sqlite` backends rank segment embeddings with brute-force cosine, and `postgres` can use pgvector. Two footprints are not well served by that design:

- Multi-million-vector workloads, where brute-force is too slow and pgvector requires keeping Postgres hot enough to hold the index.
- Managed deployments that already standardise on a dedicated vector service (Milvus, Zilliz Cloud) and want memU to reuse it.

`settings.py` already separates `metadata_store` from `vector_index` in configuration, but every shipped backend kept vectors inside its own tables. The separation was not realised in code.

## Decision

Introduce a `VectorIndex` protocol that memory repositories can delegate to when an external index is configured. The first implementation is `MilvusVectorIndex`, targeting Milvus Lite (zero-dep local), self-hosted Milvus, and Zilliz Cloud behind a single `uri`/`token` config.

- `VectorIndex` lives in `memu/database/vector_index/` and exposes `upsert`, `delete`, `delete_many`, `search`, `close`.
- `build_vector_index` in the factory constructs the provider based on `VectorIndexConfig.provider`.
- The in-memory metadata backend receives the vector index through its builder and mirrors `RecallFileSegment` mutations to it on create / delete / clear.
- `progressive_retrieve` routes segment search through the repository contract. The in-memory segment repository delegates to the vector index when present; other backends keep their existing local search paths.

Initial scope: the `inmemory` metadata backend is wired to `MilvusVectorIndex`. `sqlite` and `postgres` are planned follow-ups; their existing (brute-force / pgvector) paths remain the default so the change is additive. Until those follow-ups land, memU rejects `vector_index.provider="milvus"` with non-`inmemory` metadata stores to avoid silently ignoring the configured external index.

## Consequences

Positive:

- memU can scale vector similarity independently of the metadata store.
- Users on Zilliz Cloud or a shared Milvus cluster can reuse that infrastructure.
- Milvus Lite keeps the zero-setup local story (single file, no service) that `inmemory` already promises.

Negative:

- Two systems of record mean write amplification and a consistency window between the metadata store and the vector index.
- Scope fields are replicated into Milvus as dynamic fields, increasing storage vs. a single SQL column.
- `pymilvus` / `milvus-lite` are optional and gated behind the `milvus` extra; users picking this path accept that dependency.
- Milvus Lite 3.x uses a newer local storage format than the earlier 2.x line, so users upgrading existing local `.db` files should create a new Milvus Lite database and re-ingest their vectors.
- Milvus Lite 3.0 still imports `pkg_resources` on Python 3.13, so the `milvus` extra pins `setuptools<81` until that dependency is removed upstream.
