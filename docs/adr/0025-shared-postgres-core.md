# ADR 0025: Share the memory core across local and hosted Postgres

- Status: Proposed; design review only
- Task: MEM-13
- Related: [ADR 0002](0002-pluggable-storage-and-vector-strategy.md), [ADR 0012](0012-cloud-backed-agentic-backend.md), [ADR 0014](0014-paginated-list-all-recall-files.md)
- Follow-up context: [PR #814](https://github.com/NevaMind-AI/memU/pull/814) is paused while this boundary is reviewed. ADR number 0024 is reserved by that draft.
- [中文](0025-shared-postgres-core.zh.md)

## Problem and evidence {#problem}

A hosted integration reuses `AgenticMixin` but supplies separate Postgres repositories and overrides segment ranking and file roll-up. Sharing the mixin alone therefore does not share storage behavior, transaction guarantees or every retrieval stage. A change to memU's own Postgres backend does not automatically change that adapter.

This proposal follows source inspection of both implementations. It contains no copied private source, credentials, production records or deployment evidence. Observed adapter behavior is a compatibility input, not the definition of correct behavior.

| Area | Open-source implementation | Observed hosted integration | Alignment needed |
| --- | --- | --- | --- |
| Segment ranking | `RecallFileSegmentRepo.vector_search_segments` returns ranked records and scores; Postgres already executes pgvector ranking in SQL | A separately named native ranking method is called by a host override | Use the existing repository method and inherited retrieval stage |
| File roll-up | `AgenticMixin._collect_files` calls `list_recall_files` with `id__in` and scope | A separate fetch-by-IDs helper is called by another host override; generic filter translation does not accept `id` | Support the existing bounded ID filter with tenant predicates, then use the inherited roll-up |
| Ranking ties | Open-source Postgres orders by distance; the hosted query also orders ties by ID | Equal-score selection can differ | Agree and test deterministic ties before claiming identical results |
| Atomicity | Inmemory/SQLite implement `AtomicDatabase`; Postgres repositories commit independently | The observed adapter also opens independent repository transactions | Shared transaction ownership must precede any claim of atomic Postgres batches |
| Models | Default tables store file and segment vectors, with configurable scope models | Product tables have additional identity/position constraints and omit file-level vectors | Preserve data and behavior through explicit mappings; neither schema is a drop-in replacement |
| Scope | `UserConfig.model` validates caller-visible filters; generic repositories apply them | Authenticated tenant predicates are additionally bound inside repositories | Keep tenant binding outside caller-controlled filters, including when filters are absent |
| Embeddings | Provider-neutral clients and a client pool | Product-selected provider/configuration and usage recording | Inject the client; keep runtime product configuration and accounting outside the core |

Relevant current source: [agentic operations](../../src/memu/app/agentic.py), [segment protocol](../../src/memu/database/repositories/recall_file_segment.py), [Postgres ranking](../../src/memu/database/postgres/repositories/recall_file_segment_repo.py), [Postgres store](../../src/memu/database/postgres/postgres.py), [filter translation](../../src/memu/database/postgres/repositories/base.py), [SQL model container](../../src/memu/database/postgres/schema.py), [transaction protocol](../../src/memu/database/interfaces.py).

## Source-level Postgres comparison {#source-comparison}

Compared revisions: memU `ee7e251f4cd5f4f984577edf3233e9358b921ed9` (runtime base `12d144c`) and hippocampus-server `cca499a63d5404c156903fe9de37d076f504faca`. These are checkout observations, not assertions about the deployed version. In the evidence below, M paths are relative to `src/memu/database/postgres/`; H paths are relative to `services/memu-service/`. Private source links require repository access and are references, not copied source.

| # | Concrete difference | memU Postgres | hipp Postgres | Consequence / alignment direction | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Persistence entry paths | One synchronous Postgres repository family | Sync `MemuV4Store` for the mixin **and** async `MemoryFileRepo` for product operations | Consolidating the sync adapter alone does not unify Dashboard deletes/segment edits; inventory both call paths | M `postgres.py:30`; H `app/infrastructure/memu/store.py:514`, `app/infrastructure/persistence/repositories/memory_files.py:118` |
| 2 | Model / IDs / parent field | SQLModel; string IDs; `recall_file_id` | SQLAlchemy declarative; PostgreSQL UUID; `memory_file_id` | Requires field/record mapping and malformed-ID handling; not drop-in ORM substitution | M `models.py:31`, `models.py:65`; H `app/infrastructure/persistence/models/memu_v4_memory_file_segment.py:25`, async repository `_is_uuid:101` |
| 3 | Tenant boundary | Caller scope filters; no separate authenticated tenant binding | Sync repository binds organization/project; async selectors carry tenant conditions | Preserve a trusted restriction on all SQL paths, including mutations and retry lookups | M `repositories/base.py:67`; H sync store `_scoped:140`, async repository `_file_conditions:52` |
| 4 | Identity versus display names | Lookup compares all supplied `user_data`; generic model fields may include display names | `_scope_ids` uses user/agent IDs; display names are metadata | Agree identity fields before sharing lookup code; a display-name edit must not accidentally create another owner | M `repositories/recall_file_repo.py:95`; H sync store `_scope_ids:50`, `_find:245` |
| 5 | File uniqueness | Default `schema.get_sqlalchemy_models` does not pass `unique_with_scope`; committed baseline has no matching scoped identity unique key. Another builder supplies name-only scoped uniqueness, omitting track | Explicit unique `(organization, project, user, agent, track, name)` | Resolve open-source bootstrap/helper inconsistency and audit existing duplicates before adding a constraint | M `schema.py:75`, `models.py:164`, `migrations/versions/20260703_0001_initial_schema.py`; H `app/infrastructure/persistence/models/memu_v4_memory_file.py:12` |
| 6 | Concurrent creation | Select then insert, no explicit `IntegrityError` convergence in file repo | File insert catches unique conflict and re-reads winner; segment insert retries at most 3 times | Share tested conflict semantics, not just method names; retries are not whole-batch atomicity | M `repositories/recall_file_repo.py:95`; H sync store `get_or_create_recall_file:206`, `create_segment:375` |
| 7 | Segment shape / ownership | Text, track, parent ID, vector; ID foreign key cascades | Additional index, start/end positions and denormalized identity; index uniqueness plus ID and identity FKs, both cascade | Keep product constraints; populate extra fields within the owning transaction | M `models.py:65`; H `app/infrastructure/persistence/models/memu_v4_memory_file_segment.py:25` |
| 8 | Vector persistence | File and segment `Vector()` columns without a fixed dimension in these models | No file-vector column; segment vector dimension fixed to 1024 | Shared code must declare optional file-vector storage; changing dimensionality requires reindex/schema planning | M `models.py:57`, `models.py:73`; H file/segment models; `app/domains/memory_files/model.py:22` |
| 9 | Native ranking | `vector_search_segments`, distance ordering; optional Python fallback | `top_segments_by_similarity`, distance then ID; no corresponding fallback in that method; product HNSW partial index | Standardize repository call and tie policy; distinguish exact query checks from approximate index plans | M `repositories/recall_file_segment_repo.py:63`; H sync store `top_segments_by_similarity:314`, segment model indexes |
| 10 | Hit-file loading | Generic filters accept `id__in`; mixin rolls up bounded hits | Generic filter allowlist excludes `id`; dedicated `list_recall_files_by_ids`; host overrides roll-up | Add bounded ID filtering in the adapter, then remove duplicate host stages | M `repositories/base.py:67`; H sync store `_apply_where:65`, `list_recall_files_by_ids:152`; H `app/infrastructure/memu/engine.py:110` |
| 11 | Pagination | Same keyset `(track,name,id)` / limit+1 algorithm; default schema has no corresponding composite page index | Same algorithm plus explicit scope/track/name/ID covering index | Reuse logic; verify real query plans and migration indexes independently | M `repositories/recall_file_repo.py:41`, baseline migration; H sync store `list_recall_files_page:171`, file model indexes |
| 12 | Sessions / transactions | Own engine and session manager; repository commits; no Postgres `AtomicDatabase` implementation | Injected sync session factory, method-local transactions; async repo also owns method transactions | Introduce shared transaction ownership and engine ownership rules before claiming batch rollback | M `session.py:15`, `postgres.py:38`; H sync store, async repository module contract |
| 13 | Cache representation | Shared `DatabaseState` populated by reads/writes; segment cache does not replace an already cached ID | Sync adapter state attributes are empty protocol placeholders; records mapped from fresh rows | Do not introduce stale shared caches on the server; test rollback and cross-instance reads | M `repositories/recall_file_segment_repo.py:46`, file repo `_cache_recall_file`; H sync store `_file_record:87`, constructors |
| 14 | Physical delete / audit | File clear and segment deletion primitives; no equivalent history triggers in the committed baseline | Sync clear and async scoped delete; Dashboard uses async delete; triggers retain before-images, excluding segment vectors | Preserve cascade/audit on both paths; audit history is not a ready restore API or retention guarantee | M file repo `clear_recall_files:70`; H async repository `delete_files:244`, Dashboard `delete_file:360`, history migration `d7e2b9c4f8a3` |
| 15 | Resource support | Real resource repo, storage and ranking | `EmptyResourceRepo`; engine disables resource retrieval and HTTP drops resource writes | Keep explicit capability boundary; do not silently turn this into hosted resource storage | M `postgres.py:74`; H sync store `EmptyResourceRepo:478`, engine and public route |
| 16 | Schema lifecycle | Store construction runs memU Alembic (`create`); `validate` currently checks table presence only, even with custom model injection | Product owns its independent Alembic history, product tables, indexes and triggers | Separate external-schema mode/ownership from local bootstrap; current table-only validation is insufficient for compatibility | M `postgres.py:60`, `migration.py:36`; H `alembic/versions/` |

Evidence entry points: [memU source at compared revision](https://github.com/NevaMind-AI/memU/tree/ee7e251f4cd5f4f984577edf3233e9358b921ed9/src/memu/database/postgres), [hipp sync store](https://github.com/NevaMind-AI/hippocampus-server/blob/cca499a63d5404c156903fe9de37d076f504faca/services/memu-service/app/infrastructure/memu/store.py), [hipp async repository](https://github.com/NevaMind-AI/hippocampus-server/blob/cca499a63d5404c156903fe9de37d076f504faca/services/memu-service/app/infrastructure/persistence/repositories/memory_files.py), [hipp models](https://github.com/NevaMind-AI/hippocampus-server/tree/cca499a63d5404c156903fe9de37d076f504faca/services/memu-service/app/infrastructure/persistence/models).

## Evolution history and capability preservation {#evolution}

The hosted checkout pins `memu-cli==0.11.0b3` in `pyproject.toml`/`uv.lock`; its last dependency update is hipp commit `d29332c6` (2026-08-21). We inspected the published wheel as ZIP source without installing or executing it. Its SHA-256 `948972808846060c093c1a40fbd09b14ce6ee503169d733bb4eac8d0e42cac99` matches the hosted lockfile; PyPI records upload on 2026-08-21. This checks a pinned artifact, not a running deployment. Git dates and shared method names alone are insufficient to establish package contents.

| Capability / change | Source history | Pinned wheel and hosted evidence | Preservation / adoption decision |
| --- | --- | --- | --- |
| Native segment repository protocol and Postgres ranking | memU [`edbd422`, #652](https://github.com/NevaMind-AI/memU/commit/edbd422fcd925b3ddc57f0c84fbf24e5bb4e51b3), 2026-08-18 | Wheel already contains `vector_search_segments`. Hipp independently added native ranking and host overrides in `ad803d4a` (#644), also 2026-08-18 | Integration divergence, not a capability missing from the pinned package. Adopt the shared protocol; retain native SQL ranking and local fallback support |
| Embedding planning/batching before writes; resource in-place update | memU [`57399e5`, #651](https://github.com/NevaMind-AI/memU/commit/57399e5), 2026-08-21 | Wheel contains `_EmbeddingBatch` and resource update calls; hipp `d29332c6` adds the empty resource update adapter | Already in the pinned artifact. Preserve provider-failure-before-write behavior, batching/deduplication and local resource identity; hosted resource-disabled policy remains separate |
| Pagination input validation | memU [`abb1148`, #663](https://github.com/NevaMind-AI/memU/commit/abb11480e69cec9ca35d954b1c1ffc83ef11c100), 2026-08-26 | Wheel lacks the later mixin limit validation; hosted HTTP separately bounds page size | Later shared-core validation. Preserve it for direct local and hosted mixin calls; HTTP validation complements it |
| Fetch only hit files via `id__in` | memU [`385bdb3`, #694](https://github.com/NevaMind-AI/memU/commit/385bdb30cda7f5265368934b8008ce2b73283283), 2026-09-04 | Wheel lacks the bounded hit-ID roll-up; hipp had a separate bounded helper in `ad803d4a` | Later open-source convergence with an existing hosted optimization. Adopt current mixin bounded reads, not a whole-scope scan |
| Case/separator normalization before dedupe and lookup | memU [`42ef9fa`, #733](https://github.com/NevaMind-AI/memU/commit/42ef9fa3a8034f5817684cba23ef69fa70a58197), 2026-10-16 | Wheel lacks the current lower/space/underscore normalization chain | Later core behavior. Preserve canonical lookup/deduplication and existing-name compatibility; review product legacy collisions before upgrading |
| Reject blank/unsafe names before acknowledgement/writes | memU [`dec8676`, #803](https://github.com/NevaMind-AI/memU/commit/dec867612ea0c70a45c4af9cc1cef8b28fe0a61f), 2026-11-10 | Wheel lacks the later blank-name rejection diagnostic/guard; current source/tests reject bad input during planning | Later correctness protection. Keep entire-input validation before provider/storage work and retryable host state on rejection |
| Atomic write/re-plan and read snapshots | memU [`9e2af33`, #805](https://github.com/NevaMind-AI/memU/commit/9e2af332a58d32a830483aadc02fe58bfbefc94a), 2026-11-14 | Wheel has no `AtomicDatabase`; commit adds it for SQLite/inmemory, not either Postgres implementation | Later capability with explicit backend scope. Preserve SQLite/inmemory guarantees; Postgres must gain tested transaction participation rather than weakening the mixin or pretending current parity |
| Hosted constraints, positions, audit, resource policy | Product schema/adapters in the compared hipp checkout | Separate product requirements; the evidence does not classify each as a later memU change | Retain according to the disposition table; do not force them into the default local schema |

These dates establish the named changes, not a complete release changelog. Model/ID/cache differences without a traced introduction remain classified by current responsibility; no chronology is inferred for them. Full release qualification still needs dependency review and isolated runtime tests.

Preservation-check baseline on this documentation branch: `uv run python -m pytest tests/test_agentic.py tests/test_segment_vector_search.py tests/test_commit_concurrency.py tests/test_commit_thread_isolation.py -q` returned **133 passed, 4 skipped**. The four Postgres unit checks skipped because `pgvector` is not installed. No live Postgres or hosted integration was tested.

**Upgrade acceptance is additive to each deployment's existing supported capabilities.** Keep the current memU tests for segment-native routing and fallback, bounded roll-up, pagination validation, name normalization/rejection, batched provider-failure behavior, local resources, scoped models and SQLite/inmemory atomicity. Add product integration checks without deleting or relaxing those assertions. Any change to an existing behavior requires a separately reviewed compatibility/migration decision. Step 1 records both the artifact baseline and the capability checklist; steps 2–6 compare against current shared-core behavior and retained product policies, not against the older package as a universal baseline.

## Disposition of each difference {#disposition}

The following proposed dispositions govern the comparison and six-step plan. **Shared implementation** means reuse general memory code; **contract alignment** permits distinct storage/runtime implementations; **retain in hipp** assigns long-term product ownership. A row can contain both a reusable operation and a product-owned policy.

| Comparison rows | Disposition | Shared / aligned part | Long-term hipp ownership |
| --- | --- | --- | --- |
| 1. Sync/async paths | Contract alignment + selective reuse | Overlapping memory mutations follow the same identity, reconciliation and transaction contract | Async product repository, Dashboard orchestration and product queries can remain; delegation is evaluated per operation |
| 2. ORM / IDs | Contract alignment | Stable domain records and parent-ID mapping | Existing declarative models, UUID storage and HTTP malformed-ID translation |
| 3. Tenant boundary | Contract alignment + retain in hipp | Generic store must apply an injected mandatory trusted restriction | Authentication, organization/project resolution, RBAC and constructing the trusted restriction |
| 4–6. Identity, uniqueness, concurrent creation | Shared implementation for domain rules; contract alignment for schema enforcement | Identity/display-field distinction, per-track identity and conflict semantics | Product unique constraints, constraint names and migrations; open-source schema has its own migration |
| 7. Segment fields / ownership | Contract alignment + retain in hipp | Shared segment text/reconciliation and parent-ownership checks | Product index/position derivation, denormalized columns and composite constraints via an adapter/default |
| 8. Vector persistence | Contract alignment + retain in hipp | Explicit optional file-vector capability and vector validation interface | File-vector omission, fixed deployed dimension and model/reindex policy |
| 9–10. Ranking / roll-up | Shared implementation target | Generic native query and mixin ranking/roll-up semantics, including agreed tie handling | Index deployment/tuning and any documented approximate-search policy; implementation must satisfy its declared capability |
| 11. Pagination | Shared implementation + retain in hipp | Keyset ordering and cursor/page behavior | Product covering indexes, query-plan tuning and their migrations |
| 12. Sessions / transactions | Shared implementation for mutation mechanics; contract alignment for runtime | Transaction boundary, rollback and safe repository participation | Connection pools, engine lifecycle, async request/thread execution and product resource ownership |
| 13. Cache | Contract alignment | Correct fresh reads, rollback publication and cross-instance visibility | Hosted stateless/no-cache choice may remain; it need not adopt local `DatabaseState` caching |
| 14. Delete / audit | Selective shared implementation + retain in hipp | Existing general deletion/cascade contract; future lifecycle rules require separate review | Audit triggers, history tables, audit reads and history retention. They are not prerequisites for local installations |
| 15. Resources | Retain distinct capability | Explicit supported/unsupported behavior at the integration boundary | Hosted resource-disabled policy may remain; local resources continue to work |
| 16. Schema lifecycle | Retain separate ownership + contract alignment | Required-column/constraint capability checks for the selected operations | Product Alembic history, table names, deployment and rollback; local memU owns its own bootstrap |
| Embedding and product edge | Retain in hipp | Inject provider-neutral embedding interface and test doubles | Voyage runtime model/endpoint/key/dimension policy, usage/billing, HTTP DTO/auth/CSRF and deployment configuration |

Acceptance tests cover the selected shared contract **and** preservation of these product-owned differences. Structural equality of schemas, indexes, caches, resources, HTTP surfaces and runtime execution is not an acceptance requirement. A claimed shared operation that cannot preserve product behavior must stay behind a documented adapter boundary until the gap is resolved.

## Six-step alignment plan {#steps}

Steps are sequential; each has a reviewable exit condition. Steps 1–5 align existing capabilities. Step 6 verifies integration and rollout; deletion/recovery feature work stays paused separately.

| Step | Work / owner | Deliverable and acceptance gate |
| --- | --- | --- |
| 1. Freeze the comparison and behavioral contract | Both owners review rows 1–16; memU owns reusable checks | Agree identity/display fields, scope defaults, tie handling, file-vector omission and resource capability. Tests use synthetic vectors and cover tenant/track isolation, bounded reads, pagination and concurrency. Current differences are explicit, not asserted to pass. |
| 2. Align retrieval with the existing protocol | Hosted owner changes adapter/host; memU owner only adds agreed contract coverage/tie rule if needed | Implement `vector_search_segments` and scoped `id__in`; remove `_recall_segments` / `_collect_files` overrides and unused helpers. Actual isolated PG checks show matching scores, tie policy and SQL LIMIT/bounded-ID access. |
| 3. Make memU Postgres reusable with product models | memU owner extends concrete model/record/session/trusted-predicate seams; hosted owner supplies mapping | A synthetic product-shaped schema uses the shared repositories without auto-migration or engine disposal. All CRUD, parent checks and retry reads remain tenant-bound; UUIDs, optional file vectors and extra segment fields round-trip. Audit default schema uniqueness and migration/duplicate handling. |
| 4. Unify transactions and concurrent writes | Shared core owner plus hosted integration owner | A transaction is owned above compound operations; no inner commits split it. File/segment constraints and bounded retries are tested. Failure injection proves rollback, unchanged cache publication and cross-instance visibility on real PG. Embedding calls stay outside long DB write transactions. |
| 5. Adopt shared operations selectively | Hosted owner adopts eligible shared repos for the sync mixin path and reviews each overlapping async mutation; memU owner completes required seams | Remove duplication only for the selected general memory operations. Retain the async product repository, product projections, segment-position handling, audit and migrations as needed. Verify Dashboard/API-key behavior and nonblocking execution across retained and delegated paths. |
| 6. Integrate, upgrade and verify | Both owners run shared checks; hosted owner controls dependency/lockfile, migration and deployment | Both default memU and product-shaped PG schemas pass; HTTP round-trips pass; stage with isolated data, explicit dependency bump and rollback plan. Production rollout remains separately authorized. Resume lifecycle work only after its storage guarantees and deletion contract are reviewed. |

This PR completes the source inventory/plan portion of step 1 only; executable cross-repository checks and all runtime migration steps remain unimplemented. The intended end state is shared SQL and behavior, not merely passing method-shape checks with two independent implementations.

## Proposed boundary {#boundary}

The goal is one shared implementation for the selected general memory operations, with product-owned adapters and repositories as assigned in the disposition table. Contract-compatible implementations remain appropriate for product-specific storage and runtime concerns.

| Shared in memU | Retained by the hosted product |
| --- | --- |
| Commit identity/normalization rules, segment generation and reconciliation | HTTP DTOs, API-key/session authentication, CSRF and authorization |
| Retrieval stages, score semantics, pagination and filter contracts | Resolving the authenticated tenant and constructing a tenant-bound store |
| General Postgres CRUD, native vector ranking and transaction/session ownership | Existing table names, extra columns, constraints, audit triggers and product migrations |
| Backend contract checks and generic extension seams | Runtime embedding provider/model/endpoint/credential selection, usage ledger and billing |
| Future lifecycle rules once separately agreed | Deployment configuration, dependency pinning, rollout and rollback |

Generic Voyage support may remain open-source. The hosted choice to use Voyage, its runtime settings, credentials and accounting remain product-owned. The core stays embedding-only and must not depend on a product LLM factory or settings singleton.

Scope validation and tenant authorization are different responsibilities. A trusted tenant restriction is immutable store context; request filters can narrow it but never replace or widen it. An empty filter must still be tenant-bound. Do not add tenant credentials or product authorization logic to the public service API.

## First implementation slice: reuse existing retrieval contracts {#first-slice}

No new public entry point, repository method or configuration flag is needed for this slice:

1. Establish the existing ranking/roll-up contract with fixed synthetic vectors and scoped records. Define behavior for equal scores, absent vectors, empty IDs and track filters. Use the same checks against both implementations.
2. In the hosted adapter's owning workspace, implement `vector_search_segments` using its current native query. Accept `id`/`id__in` in file filtering, preserving unconditional authenticated tenant predicates. This must remain a bounded SQL query, not a full table read followed by Python filtering.
3. Remove the hosted ranking and roll-up overrides after the shared `AgenticMixin` passes those checks unchanged. Remove adapter-only helpers when no caller remains.
4. Compare authoritative search responses in an isolated hosted environment. Preserve scores, file roll-up, track/scope filtering and bounded query behavior. Explicitly review tie-order changes rather than silently calling them parity.

This slice removes duplicate service algorithms. It does not yet consolidate the two native SQL implementations; that is the next slice. It is independently reviewable and does not require rewriting product tables or changing embedding models.

## Next slice: consolidate Postgres implementation {#postgres}

First audit the existing `sqla_models`, record conversion, scope-model and session hooks. Extend those concrete seams only where the second real consumer requires it; do not introduce a new storage framework or configurable query language.

The shared repositories need to support:

- Mapping domain fields to existing columns, including the segment parent ID, plus explicit conversion to memU records. Product-only segment position/index fields are supplied by a narrow adapter hook or database default within the same transaction.
- A mandatory trusted predicate on **every** read and write when hosted, including ID lookups, segment-parent checks, clear operations, retries and vector searches. The default local store remains usable without product tenants.
- Injected session/transaction ownership. Supplying a product session factory must not accidentally dispose its engine. Compound operations must not be split by inner `commit()` calls, and caches must not publish rolled-back state.
- A documented distinction between user/agent identity and display metadata; exact-match and omitted/`None` read-filter semantics must be agreed before changing them. Do not silently migrate unscoped local data into a hosted default scope.
- Explicit support for the hosted file-vector omission. File vectors are not currently used by segment-based retrieval, but future writes must not assume their persistence. Segment vectors remain required for searchable content.

Existing product schema/migrations remain product-owned. Shared lifecycle or repository changes must come with explicit migration requirements for each supported schema. Do not point open-source bootstrap at product tables or let it create/alter them automatically. Preserve IDs, timestamps, owner identity, track/name uniqueness, segment ownership/cascades and audit behavior. Baseline backup and migration rollback must be reviewed before any production change.

If a model cannot satisfy an operation, expose a clear unsupported contract during integration rather than accepting and silently dropping behavior. The target adapter owns product-specific mapping, policies and operations. Selected shared CRUD, ranking and future lifecycle operations delegate to the common core where compatible; product-specific SQL and async repositories remain valid under their documented contracts.

## Compatibility checks and release gate {#validation}

Use a small reusable set of pytest assertions/fixtures in memU's test support, importable by the hosted integration without depending on a repository checkout's `tests` package. Its packaging mechanism is an implementation detail to settle in the first slice; no new package or plugin framework is proposed. Run it on actual isolated Postgres instances for SQL behavior; inmemory/SQLite checks alone do not prove Postgres parity.

| Check | Required result |
| --- | --- |
| Identical synthetic corpus/query vectors | Same scoped top-k scores and roll-up; a deliberate, tested tie policy |
| Two tenants, users, agents and same-name files across tracks | No cross-boundary reads or writes, even with empty filters or IDs belonging elsewhere |
| Missing vectors, empty IDs, unknown filters | Consistent documented results or visible errors; no widened query |
| Recommit and concurrent insert | Stable file identity, correct segment reconciliation and preserved constraints |
| Pagination | `(track, name, id)` ordering, no duplicate/skip on a static corpus, correct cursor termination |
| SQL access pattern | Ranking uses ORDER BY/LIMIT in SQL; roll-up fetches only hit IDs; no whole-corpus load |
| Transaction failure and two-instance reads | All-or-nothing where promised, correct rollback/cache state and durable visibility |
| Product schema compatibility | Existing IDs, extra fields, cascades and audit behavior preserved |
| Embedding injection | Synthetic client works without product secrets; runtime settings and usage stay outside core |

The transaction checks are a gate for the shared transactional Postgres slice, not a claim that current independent-commit implementations pass. Retrieval alignment can land first without silently broadening its guarantees.

The product pins a released memU version. Sharing source does not bypass versioning: publish through the normal authorized release process, explicitly update the product dependency/lockfile, run contract and HTTP integration checks, and deploy to an isolated environment before rollout. Keep the previous dependency/deployment version available for compatible rollback; schema downgrades require their own plan. Publishing, deployment and live database changes are separate actions.

The same checks should run in both repositories' CI when the product bumps memU. Protocol shape checks catch missing methods; behavioral checks catch implementations that satisfy the shape but differ semantically. There is no automatic online effect from an open-source commit.

## Scope, decisions and acceptance {#acceptance}

This PR proposes the boundary and sequence only. It changes no runtime code, storage schema, dependency version or deployed service. No backend parity suite or hosted runtime check has been executed as part of this document-only change. Source references and bilingual Markdown links are checked.

Review decisions:

1. Adopt retrieval-contract alignment as the first implementation slice.
2. Adopt shared Postgres repositories with explicit model/tenant/session seams as the target, preserving product schema ownership.
3. Agree on the contract-check distribution and the owning workspace for hosted changes before implementing that integration.

Acceptance for the subsequent migration requires reuse of the selected common operations, passing their behavioral checks, and preservation of each retained product responsibility in the disposition table. Removing duplicate host overrides is an initial measurable result; retained product SQL/repositories are reviewed by responsibility rather than counted as incomplete migration. Lifecycle work resumes only after its required shared storage guarantees and separate deletion contract are agreed; no retention policy is decided here.
