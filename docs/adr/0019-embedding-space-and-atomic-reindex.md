# ADR 0019: Embedding Spaces Are Store State and Reindex Atomically

- Status: Proposed
- Date: 2026-09-01
- Scope: local `MemoryService` storage and the `memu reindex` command

## Context

`commit_results` deliberately reuses a vector when its source text is unchanged.
The store previously recorded no provider/model identity, so changing embedding
configuration could silently compare coordinates from two same-dimensional
models or fail later on a dimension mismatch. CLI config checks cannot enforce
this for SDK callers, environment overrides, or concurrent processes.

## Decision

Each local store has one active embedding space, identified by a SHA-256 digest
of the normalized, non-secret provider, model, base URL, and embeddings endpoint.
API keys, URL credentials, queries, and fragments are excluded.

Every commit and retrieval checks this identity before using vectors. SQL
repositories repeat the check in the same transaction as each vector write, so
a process that planned a commit before another process reindexed cannot write
old-space vectors afterward. A legacy store with vectors but no identity is not
guessed; it must be reindexed.

`memu reindex` reads all Resource captions, RecallFile names/descriptions, and
segment texts, deduplicates them in one embedding batch, and only then replaces
all vectors plus the active identity in one backend transaction. Provider
failure happens before storage changes; transaction failure rolls everything
back.

## Consequences

- Changing provider, model, or endpoint is explicit and may incur a full
  embedding cost.
- Retrieval never runs an expensive migration implicitly.
- One database cannot intentionally mix embedding models. Use separate stores
  when different agents require different spaces.
- The identity detects configuration changes, not an upstream provider changing
  a model's semantics without changing its advertised endpoint/model contract.
