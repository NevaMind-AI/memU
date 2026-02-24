# ADR 0002: Use Pluggable Storage with Backend-Specific Vector Search

- Status: Accepted
- Date: 2026-02-24

## Context

memU must support:

- zero-setup local development
- lightweight persisted deployments
- production deployments that need scalable vector similarity

No single storage engine fits all three cases.

## Decision

Adopt repository-based storage abstraction behind a `Database` protocol, with selectable providers:

- `inmemory`: in-process state, brute-force similarity
- `sqlite`: file-based persistence, embeddings stored as JSON text, brute-force similarity
- `postgres`: SQL persistence, pgvector-enabled similarity when configured

Vector behavior is backend-aware:

- brute-force cosine search remains available for portability
- Postgres can use pgvector distance queries when vector support is enabled
- salience ranking (reinforcement/recency-aware) uses local scoring logic

## Consequences

Positive:

- one service API works across local and production footprints
- clear backend contracts through repository interfaces
- predictable fallback behavior when native vector index is unavailable

Negative:

- duplicate repository logic across backends
- behavior/performance differences between providers
- SQLite and in-memory vector search does not scale as well as indexed pgvector
