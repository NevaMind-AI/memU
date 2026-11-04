# 0021: Atomic memory commits and consistent retrieval snapshots

## Status

Proposed.

## Context

A commit plans resource and recall-file changes, obtains embeddings, then updates
resources, files, and segments. Embedding is asynchronous; another process can
change the same records while a plan waits. Applying that old plan can leave
search segments that no longer correspond to the file or create duplicate
resources. A storage error between writes can also expose only part of a batch.
Reads spanning several repository calls can observe different committed states.

A missing scope field has two meanings: read filters omit it to search across
that dimension, while a write must target the exact scope, including null fields.
Treating null as a wildcard during a write lets a default-scope commit overwrite a
more specific owner's data.

## Decision

A backend exposes a synchronous atomic write unit and a read snapshot. A commit
first requests embeddings without holding a database lock. Inside the atomic
unit it re-plans from current records. If this plan needs a new vector, it
releases the unit, obtains the missing vector, and retries. Once all vectors are
available, resource, file, and segment changes commit or roll back together.
The write phase contains no await point.

In-memory storage protects shared state with a reentrant lock and restores it on
failure. SQLite uses a single `BEGIN IMMEDIATE` transaction. PostgreSQL uses a
transaction-scoped advisory lock shared by memU writers, and a single SQL
transaction. Repository-level commits flush within the owning unit of work.
Retrieval uses a consistent read snapshot: a lock in memory, a SQLite read
transaction, and a PostgreSQL repeatable-read read-only transaction.

Write lookups match every scope field exactly, including null. Public read filters
retain their existing wildcard behavior for omitted or null fields.

## Consequences

Writers targeting the same store serialize during database work, but provider
latency is outside the lock. Replanning may require another embedding request
when a conflicting commit changed what needs embedding. A process crash releases
SQL locks and rolls back uncommitted SQL changes. The advisory lock only
coordinates writers using this unit of work; direct SQL writes by other clients
must provide their own coordination. SQLite and PostgreSQL maintain their
existing schema and need no migration.

Tests must cover overlapping commits, rollback at each write stage, provider
failure and cancellation, scope isolation, reader snapshots, independent SQLite
processes, and real PostgreSQL transaction behavior.
