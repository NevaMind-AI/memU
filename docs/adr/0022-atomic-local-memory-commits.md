# 0022: Atomic local memory commits

## Status

Proposed.

## Context

Concurrent `commit_results` calls can plan against the same old file while
awaiting embeddings. Applying both diffs can leave search segments inconsistent
with the final body, or duplicate a resource. Repository methods also commit
individually, so a storage failure can publish only part of a batch.

## Decision

Adapt the transaction and concurrency work from
[PR #785](https://github.com/NevaMind-AI/memU/pull/785) by
[Cookie0103 (Ke Chen)](https://github.com/Cookie0103), focusing on
SQLite and in-memory storage as requested in its review.

Keep `Database` unchanged and introduce an optional `AtomicDatabase` capability.
SQLite and inmemory implement atomic writes and consistent read snapshots.
Backends without that capability keep their existing storage behavior. This
change does not modify PostgreSQL, Cloud, SQL schemas, or identity scope matching.

Plan and obtain embeddings outside write ownership. Re-plan inside the atomic
unit using current stored records. If that plan requires another vector, release
the unit before requesting it and retry. Once all vectors are ready, publish
resources, RecallFiles and segments together, with no await inside the write
unit. Materialize the response before releasing ownership.

SQLite uses `BEGIN IMMEDIATE` and a shared SQLAlchemy session. Repository-level
`commit()` calls flush within the unit; the owner commits or rolls back the batch.
A read transaction gives each retrieval or listing page a consistent snapshot.
Inmemory uses a reentrant state lock and restores copied state on failure.
SQLite also restores its caches on rollback. Public operations sharing a store
coordinate cache access through that state lock.

## Consequences

SQLite writers serialize during database work, including across processes.
Embedding network latency does not hold a database transaction. Snapshot copying
costs memory proportional to the cached state; replace it with a narrower undo
mechanism if measured cache size makes this expensive.

The transaction boundary is one `commit_results` call. Direct repository writes
must participate in the same coordination to receive the same guarantees.
Pagination does not hold a snapshot across separate API calls.

Concurrent full-body updates still use last-writer-wins semantics. Re-planning
keeps the index consistent with the submitted body; it does not merge candidate
bodies or reject a candidate based on an outdated input revision. Expected-revision
checks, durable retry identifiers, and maintenance completion markers require a
separate contract. Atomic publication does not validate semantic fidelity or
change the meaning of fact time.

Tests cover overlapping file/resource commits, separate SQLite services and
processes, rollback at each write stage, cancellation and re-embedding failure,
consistent retrieval, initial planning and response isolation, and compatibility
with the original database contract.
