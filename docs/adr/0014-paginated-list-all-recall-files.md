ADR 0014: Paginated `list_all_recall_files`

- Status: Proposed
- Date: 2026-07-26
- Builds on: ADR 0012 (cloud-backed agentic backend), ADR 0007 (three memory
  lines / tracks), ADR 0003 (user scope in the data model)
- Scope: making `list_all_recall_files` return one bounded page per call across
  both the local and cloud backends, and having the only two callers reassemble
  the full set by following a cursor. It does not change `progressive_retrieve`,
  `commit_results`, or the `where` vocabulary.

## Context

`list_all_recall_files` returns every recall file in scope in a single
response. Today `AgenticMixin.list_all_recall_files` calls
`recall_file_repo.list_recall_files(where)`, which loads the whole result set,
and both callers consume all of it at once:

- bridging `prepare` mirrors the entire store to disk;
- the `list-files` CLI prints the whole list.

As a scope's memory/skill set grows, that single response grows without bound:
one large DB read, one large serialization, one large HTTP body. We want a
bounded page size.

Two facts about the topology constrain the design:

1. **There is one implementation, not two.** The hosted service does not have
   its own query code for this operation — `memu-service` runs open-source
   memU's `AgenticMixin` unchanged (`MemuAgenticHost(AgenticMixin)`) over its
   own storage adapter, and the HTTP route returns the mixin's dict untouched
   ("the wire shape is memU's by construction"). So the paginated *response
   shape* must be born in the mixin; the cloud client and the server route
   cannot synthesize a shape the mixin does not produce.

2. **Both execution paths must stay byte-for-byte identical.** `local` runs the
   mixin in process; `cloud` runs the same mixin behind one HTTP roundtrip
   (ADR 0012). Pagination — page size, ordering, cursor encoding — therefore
   belongs to the mixin and its repositories, not to any one transport.

## Decision

### Paginate at the source, keyed on `(track, name, id)`

`AgenticMixin.list_all_recall_files` gains `cursor` and `limit` parameters and
returns `{"recall_files": [...], "next_cursor": <token-or-null>}`. A `null`
`next_cursor` means the last page. The page is produced by a new repository
method (below), ordered by the composite key **`(track, name, id)`**.

Why `(track, name)` is the ordering key — the crucial decision:

- **It is the domain's own identity, so it is unique by construction, not by
  accident.** A recall file is keyed by `name` within its `track`
  (`memory`/`skill`) — see `commit_results`. Pagination always runs inside a
  fixed `(user_id, agent_id)` scope, so within one paging sequence `(track,
  name)` is unique. Uniqueness is the one hard requirement for correct paging:
  with no ties, no page can skip or duplicate a row, which is exactly what a
  caller reassembling the full set needs.
- **It is immutable under the write path.** There is no in-place rename; a
  "rename" is delete-then-create. A row therefore never changes its sort
  position mid-pagination, which is what keyset resumption relies on.
- **It produces a meaningful order for free** — stable alphabetical `list-files`
  output, and a debuggable cursor — where the primary-key alternative (a random
  UUID, `RecallFile.id`) would order arbitrarily and carry no business meaning.

`id` is appended as a final tiebreaker (`ORDER BY track, name, id`). `(track,
name)` is already unique today, so this is defense-in-depth: it makes the total
order unconditional if the uniqueness invariant is ever relaxed (a migration
window, soft-deleted duplicates) at zero cost.

### Keyset, not offset

The cursor encodes the last row's `(track, name, id)` and each page resumes with
`(track, name, id) > (cursor)`. Offset pagination drifts under the concurrent
commits that `prepare` races against: a delete positioned before the offset
shifts every later row up and silently skips one. Keyset over an immutable
unique key does not drift. The cursor is an opaque token (base64 of the tuple)
so callers cannot depend on its internals.

### Page at the repository, not in memory

The page is a bounded repository query
(`WHERE scope AND (track,name,id) > cursor ORDER BY track,name,id LIMIT n+1`),
added as a new method rather than by slicing the existing full-fetch in the
mixin. In-memory slicing would re-read and re-sort the entire table on every
page — on the multi-tenant server, N page calls become N full scans, which is
worse than the single read we set out to shrink. A keyset query touches only one
page's worth of rows per call. (The in-memory backend "queries" a sorted list,
so paging there is a trivial slice — but the method signature is uniform.)

The new method is additive:

```
list_recall_files_page(where, *, after, limit)
    -> (ordered list[RecallFile], next_after | None)
```

The existing `list_recall_files(where) -> dict[str, RecallFile]` is left
untouched: its other callers — the `_collect_files` file roll-up and the
per-track lookup in `_commit_recall_files` — genuinely need the full,
unordered set, and must not be forced through a cursor.

### One page per call at the transport; callers reassemble

`CloudMemoryClient.list_all_recall_files` forwards `cursor`/`limit` as query
parameters and passes the paginated body through unchanged — one page per call,
no client-side loop. Reassembly lives in the callers, where it composes with
work they already do per item:

- bridging `prepare` follows `next_cursor`, writing each page to disk as it
  arrives — no change to its per-file mirror logic, and the whole store is never
  held in memory at once;
- the `list-files` CLI follows `next_cursor` to gather the full list before
  printing (its contract is "show everything").

`limit` defaults to a fixed page size (`DEFAULT_PAGE_LIMIT`); callers do not set
it.

## Server-side changes (hippocampus-server)

The mixin change flows to the server through the pinned memU git dependency; the
service's own code changes only to thread the two new parameters through and to
implement the paged query on its storage adapter:

1. **HTTP route** (`app/interfaces/http/api/memory_files.py`, `GET
   /api/v4/memory`): accept `cursor: str | None` and `limit: int` as `Query`
   parameters (bound `limit` with `ge=1, le=<max>`) and forward them. The return
   value is still the mixin's dict, passed through untouched, so `next_cursor`
   reaches the wire for free.
2. **Engine** (`app/infrastructure/memu/engine.py`,
   `MemuAgenticEngine.list_all_recall_files`): accept `cursor`/`limit` and
   forward them into `host.list_all_recall_files(where=where, cursor=cursor,
   limit=limit)`. No shape work — the result already passes through `_run`
   unchanged.
3. **Storage adapter** (`MemuV4Store`'s recall-file repository): implement
   `list_recall_files_page` with the same keyset predicate and
   `ORDER BY track, name, id` over the multi-tenant schema. This is the one place
   the server supplies its own query code (it satisfies memU's repository
   protocol), and it must order identically to memU's own repositories or the
   two execution paths diverge. An index covering `(scope…, track, name, id)`
   keeps each page seek-only.

## Consequences

Positive:

- Response, serialization, and DB-read size per call are bounded by `limit`
  regardless of how large a scope grows.
- Local and cloud paths remain identical: same ordering, same cursor, same page
  shape, because pagination lives in the shared mixin + repository contract.
- `prepare` never materializes the whole store in memory; it streams pages to
  disk.
- The ordering key is the domain identity, so correctness (no skips/dups) does
  not depend on an incidental property.

Costs:

- The repository protocol gains a method that every backend must implement
  (SQLite, in-memory, Postgres here; `MemuV4Store` on the server). A backend
  that forgets it, or orders it differently, breaks paging silently.
- `list_all_recall_files` is no longer a single call; both callers carry a
  cursor loop, and any future caller must remember to follow `next_cursor`
  rather than reading one page and stopping.
- The cursor's meaning (`(track, name, id)` keyset) is now part of the
  cross-repo contract; changing the sort key later invalidates in-flight cursors.

## Out of scope

- Paginating `progressive_retrieve` (already bounded by `top_k`) or
  `commit_results`.
- Widening the `where` vocabulary (ADR 0012 keeps cloud reads to exact
  `user_id`/`agent_id`).
- A stateful/snapshot cursor that hides concurrent inserts appearing on a later
  page; keyset gives read-committed semantics, which is sufficient for `prepare`
  (a missed just-created file is picked up on the next run).
- Total-count or `has_more`-beyond-`next_cursor` metadata.
