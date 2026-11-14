# 0022: Atomic Local Commits

## Status

Accepted.

## Context

Concurrent commits can plan against the same stored segments while awaiting embeddings. Publishing those stale differences can leave searchable segments that disagree with the final RecallFile body. Independent repository commits can also leave a partially applied batch after a storage failure.

## Decision

Add an optional `AtomicDatabase` capability with synchronous `atomic()` and `snapshot()` context managers, preserving the existing `Database` contract. SQLite and inmemory implement this capability; PostgreSQL and backends without it retain their existing storage guarantees.

One `commit_results` call is the atomic boundary across resources, RecallFiles, and segments. Initial planning reads a snapshot. Embedding requests run outside write ownership. After acquiring write ownership, the service re-plans against current records. If more vectors are needed, it releases ownership before requesting them and then re-plans again. The write phase contains no `await`, and response serialization completes before ownership is released.

SQLite uses `BEGIN IMMEDIATE` to serialize writers, including separate processes. Repository calls borrow one session, with repository-level commits flushing into the enclosing transaction. A failure rolls back the database transaction and restores cached state. SQLite reads share an explicit read transaction for each snapshot.

Inmemory uses a shared state lock for writes and snapshots, with copies of state restored on failure. Both backends restore dictionaries and lists in place so repository container references remain valid.

Each `list_all_recall_files` or `progressive_retrieve` call holds its own snapshot through response serialization. Separate calls, including successive listing pages, do not share a snapshot.

## Consequences

Successful commits leave file bodies and searchable segments consistent. Embedding failure writes nothing; storage failure rolls back the entire batch on SQLite and inmemory.

Concurrent full-body updates use last-writer-wins semantics. Re-planning reconciles the index with the submitted body; it does not merge edits or check an expected revision. This guarantee applies to the service entry points, not independent repository calls made outside these contexts.

Rollback preparation deep-copies cached resources, files, and segments while holding the state lock. Its time and additional memory cost grow with cached state size; an undo log is a possible replacement if that cost becomes significant. SQLite still permits one writer at a time, and snapshots may delay writers depending on journal mode.

Regression coverage is in `tests/test_commit_concurrency.py` and `tests/test_commit_thread_isolation.py`, alongside the existing dual-backend service tests.
