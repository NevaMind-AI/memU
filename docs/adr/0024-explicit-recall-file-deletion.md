# ADR 0024: Explicit RecallFile deletion and recovery

- Status: Proposed; contract review required before lifecycle implementation
- Task: MEM-13; consumer: MEM-9
- Scope: RecallFile lifecycle in local storage, Cloud transport, CLI and host mirrors
- [中文](0024-explicit-recall-file-deletion.zh.md)

## Verified starting point

`AgenticMixin`, `AgenticMemoryBackend` and `CloudMemoryClient` expose exactly
`list_all_recall_files`, `progressive_retrieve` and `commit_results`.
`commit_results` upserts `(scope, track, name)`; omission never deletes.
`hosts/bridging/manifest.py` records only relative paths and byte hashes and
`diff_tracked` ignores missing files. Both bridging and developer memorize use
that function. It contains neither backend identity nor scope nor revision.

Both prepare paths write listed files into the mirror; neither removes surplus
local files. Consequently, simply hiding a backend file is insufficient: an old
mirror could later upsert it again. Local file deletion alone is also insufficient:
prepare can bring the authoritative file back.

Repositories have `clear_recall_files(where)` and `delete_segments_for_file(id)`,
but no recoverable lifecycle. Calling those methods sequentially is not a safe
public deletion API. SQLite/inmemory implement `AtomicDatabase`; Postgres does
not, and its repository methods commit independently. Records have timestamps,
not a concurrency revision or deletion marker.

Cloud currently maps GET/POST `/api/v4/memory` and POST
`/api/v4/memory/search`. The client does not expose deletion. ADR 0014 describes
a private server adapter, but that source is unavailable in this workspace.
An unauthenticated GET of `https://api.memu.so/openapi.json` returned 404 during
this investigation. This establishes no deletion or recovery capability either
way; a server contract and isolated test scope are still required. No production
memory was read or mutated to test deletion.

## Recommendation

Use an explicit delete command backed by soft deletion. Keep ordinary commits
additive/updating. A missing file may be reported as a local discrepancy, but
never authorizes deletion. First version executes explicit lifecycle commands
directly; staging them through a filesystem outbox is unnecessary.

| Choice | Intent and safety | Compatibility and recovery |
| --- | --- | --- |
| Infer deletion from mirror absence | Cannot distinguish accident, incomplete listing, wrong directory, old baseline or intent | Changes ordinary commit semantics; requires authoritative baseline and recovery anyway |
| Explicit deletion with a revision | Selects one authoritative target; rejects stale decisions | Additive opt-in, backend trash supports recovery |
| Explicit staged intents consumed by commit | Safe only with the same target/revision checks and durable receipts | Possible later, but adds outbox acknowledgement and partial-failure handling |

Keep the service's three entry points. Extend `commit_results` with optional
`recall_file_operations`, accepting explicit `delete`/`restore` records. A lifecycle
batch must contain no ordinary recall-file/resource writes. Each operation is
atomic; the whole lifecycle batch is atomic. Callers doing a large cleanup submit
one target per call initially, so independent successes are evident and retryable.
Extend `list_all_recall_files` with `state="active"|"deleted"`, default active,
for scoped trash listing. Pagination cursors are valid only within the same
scope/state. These are proposed signature changes, not available calls today.

This avoids adding a fourth service entry point. CLI `delete-file` and
`restore-file` are user-facing verbs which call `commit_results`. Neither command
advances session cursors or treats a successful deletion as transcript recording.
The service remains embedding-only.

## Exact target and request contract

Proposed example (not currently executable):

```python
await backend.commit_results(
    user={"user_id": "isolated-user", "agent_id": "isolated-agent"},
    recall_file_operations=[{
        "operation": "delete",
        "operation_id": "caller-generated-uuid",
        "id": "backend-file-id",
        "track": "memory",
        "name": "exact-backend-name",
        "expected_revision": 7,
    }],
)
```

The backend validates all fields, rejects unknown operation fields and invalid
tracks, and matches **ID + exact name + track + every configured scope field**.
Names are not normalized during lifecycle lookup. A missing/mismatched target is
an error; it never widens to a name search or wildcard. Explicit `skill` targets
are allowed; `resource`, workspace files and original resource URLs are outside
this operation. No directory, prefix, wildcard or delete-all form is provided.

Scope is derived using `UserConfig.model`. Validate keys via `_normalize_where`,
then enforce exact equality and complete scope (no `__in`, omitted fields or
`None` meaning wildcard). A locally unscoped database is allowed only when its
configured model has zero scope fields. Existing default-model unscoped rows
need an explicit migration to concrete scope values before lifecycle operations.
Cloud's literal `default` scope is an explicit exact value; local `None` must not
silently become that value. Any extra Cloud server/project tenant identity is
bound by authenticated server configuration and receipts, never client input.

Callers first list the authoritative target and use its ID/revision. Local
manifests are optional hints, never authority. A stale manifest requires fresh
listing; a missing/incomplete one cannot authorize deletion. A changed target
requires renewed review using its new revision, not an automatic revision retry.
An ordinary rename remains a new file plus an explicit deletion of the old ID;
there is no inference from similarity or a removed pathname.

## Storage, concurrency and recovery

Add `revision` (positive monotonic integer) and nullable `deleted_at` to RecallFile.
Existing records start active at revision 1. Add a durable operation receipt keyed
by `(exact scope, operation_id)` containing the canonical request digest and result.
Retain receipts and deleted rows until explicit future purge policy; no automatic
purge is included. **Recommendation: indefinite retention for version 1**, which
has a storage/privacy cost and is not secure erasure. This retention choice needs
user agreement before implementation. Recovery lasts while the database survives;
inmemory trash disappears when that process/database is discarded. SQLite and
Postgres retain trash across restarts and still require normal database backups.

Delete under one write transaction/lock:

1. Check for an existing receipt first. Same ID and identical request returns the
   original result, even if a restore has since occurred. Reused ID with different
   input conflicts.
2. Validate exact scope and target; compare revision under write ownership.
3. Mark deleted, increment revision, delete all of that file's segments/vectors,
   and store the acknowledgement in the same transaction. Keep content,
   description, file-level embedding and identity for recovery.

Ordinary listing, every file lookup/vector search and all segment searches must
exclude deleted files. Segment searches additionally filter/join the owning active
file to exclude legacy orphan/stale segments before top-k ranking. Filtering only
after top-k would let stale hits crowd out valid results. Deleted descriptions and
file-level embeddings never participate in active recall. SQL caches must be
invalidated/published only after commit; warm caches and other service instances
must observe the same lifecycle state.

Ordinary commit against a deleted `(scope, track, name)` conflicts, even without a
revision. The name remains reserved by its tombstone. A stale mirror therefore
cannot resurrect it. Active writes and lifecycle writes both increment revision;
CAS and row locking serialize a concurrent update versus deletion. If update wins,
delete conflicts; if delete wins, update conflicts. No name reuse or implicit
restore is provided. A second delete with a new operation ID and the current deleted
revision returns `already_deleted` without extending retention; stale revisions
conflict. An analogous repeated restore returns `already_active`.

Restore uses the same target fields, `operation="restore"` and the current deleted
revision. Rebuild segments with the current track slicing rules and embedding
profile, including the description embedding, before publication. Provider failure
leaves the file deleted. Recheck revision under write ownership after embedding;
CAS conflict leaves storage unchanged. Publish active file, segments, revision and
receipt atomically. Preserve the stable file ID, scope, name, content and original
creation time. There is no replace-another-file option. Incompatible embedding
model changes require the repository's normal reindex procedure across the active
corpus; lifecycle restore does not migrate a mixed-model corpus.

For retry after timeout/crash, reuse the exact operation ID and payload and obtain
the stored result. Receipt plus mutation must commit together. An error before
commit changes nothing. A failed batch publishes nothing and yields a visible
error; a successful batch returns one receipt per request including
`operation_id`, target identity/scope, resulting revision, state, `deleted_at`
and retention policy. Replaying a successful receipt reports historical success,
not the current state; refresh the target before further operations. Failure of
local cleanup after backend success must not trigger a newly identified mutation.

## Host and mirror rules

- Plain file loss, empty directories, wrong roots, old/missing/incomplete manifests
  and partial prepare listings never generate delete operations.
- Explicit CLI targets come from authoritative listing. Show exact backend,
  scope, ID, track, name and revision for review; require explicit target arguments.
  Existing authorization governs execution; the command does not infer consent
  from filesystem state.
- After acknowledgement, remove only the matching owned mirror entry if its bytes
  still match the reviewed snapshot. A locally edited file is preserved with a
  visible conflict. Persist a receipt for cleanup retry; no session cursor moves.
- Mirror identity metadata must be separate from editable Markdown: backend
  fingerprint, exact scope, ID, track, name, revision and content hash. Only a
  complete successful listing can publish a new reconciliation generation. An
  interrupted/partial listing cannot prune anything. Legacy hash-only manifests
  continue working for ordinary commits, but are not deletion metadata.
- Reconcile stale owned mirrors during prepare using authoritative active/trash
  state. Never sweep unknown user files. Retrieval's mirror writer must observe
  backend revisions so an in-flight stale retrieval cannot recreate a deleted
  mirror after reconciliation. The tombstone write guard still protects the
  backend if a stale local file survives.
- Restore fetches the new authoritative record and refreshes its mirror/identity
  metadata. Preserve a conflicting local edit and report its path. Backend success
  with mirror failure remains success with a visible cleanup requirement.

## Backend and Cloud implementation gate

Before enabling lifecycle commands, implement the protocol in inmemory, SQLite,
Postgres and the actual hosted adapter. Add a transaction-owning lifecycle repository
operation if a shared `AtomicDatabase` extension would unnecessarily alter existing
commit behavior; independent repository commits are unacceptable. SQLite must
upgrade existing databases as well as bootstrap new ones; Postgres needs a new
Alembic revision. Scope/identity uniqueness includes deleted rows; receipts have a
scope/operation ID unique constraint. Test rollback and multi-instance visibility.

Cloud requires maintenance-owner confirmation of:

1. Existing delete/restore capabilities, route/schema and auth/scope requirements;
2. Transaction/CAS/receipt guarantees in its storage and independent slicing path;
3. Trash retention, list state and migration/backfill behavior;
4. A non-production scope and version for end-to-end verification.

An unknown optional field could be silently ignored by an old server. Advertise
an explicit `recall_file_lifecycle_v1` capability in list responses; Cloud CLI must
fail closed without it, and reject success responses lacking matching operation
receipts. An old server must never produce a false delete success. No guessed
DELETE endpoint or fallback to clearing content is permitted. Private server
changes belong to its owning workspace/maintainer; this task does not deploy them.

## Validation and delivery status

Implemented in this change: regression coverage in `tests/test_agentic.py` across
inmemory and real SQLite, bridging and developer memorize, missing file, empty
mirror, missing/incomplete/stale manifest and wrong root. It checks authoritative
file identity/content plus searchable segments and resources survive ordinary
commit. Embeddings are deterministic test doubles; this is not Cloud verification.
Validation: `uv run python -m pytest tests/test_agentic.py -q` passed all 113 tests,
including 24 new loss scenarios. Ruff lint/format, `git diff --check` and relative
ADR Markdown link checks passed. No site source changed.

Lifecycle behavior below is an implementation acceptance plan, **not passed tests**:

| Scenario | Required backend observation |
| --- | --- |
| Delete memory; same name in another scope/track | Only exact target absent from active reads, descriptions and segment/vector recall; others unchanged |
| Restore and restart | Original ID/content readable, current segments callable and retrievable; SQL durability preserved |
| Lost response, repeated operation ID, changed payload | Same receipt once; changed-payload conflict; no re-delete after later restore |
| Concurrent write/delete/restore from two instances | One serialized result or revision conflict; no partial state or stale cache |
| Failure at each mutation/receipt boundary | Entire batch rolls back; identical retry succeeds |
| Provider failure during restore | Still deleted, no partially searchable segments |
| Legacy/empty/wrong/partial mirror and stale retrieval | No implicit backend removal or resurrection; conflicts visible |
| Same-name tombstone and stale ordinary commit | Conflict; no implicit restoration |
| Old Cloud server / missing capability or receipt | Visible unsupported/protocol error, never false success |
| Cloud isolated delete/restore | Real authoritative reads and searches confirm exclusion/restoration, unrelated records unchanged |

Pending decisions: agree on this three-entry-point extension and indefinite
recoverable retention, and obtain the hosted contract/isolated test scope. Until
then no lifecycle command/API is available, no storage schema is changed, and
MEM-9 must not use the proposed example to remove production memories. Once
implemented, MEM-9 must refresh exact targets, use one stable operation ID per
reviewed target, save receipts, verify active listing/search, and use trash revision
for restore. Snapshot counts in MEM-9 are historical, not a current deletion list.
