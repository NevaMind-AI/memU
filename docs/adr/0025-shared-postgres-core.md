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

## Proposed boundary {#boundary}

The goal is one shared implementation of general memory behavior and Postgres operations, with a small product adapter. Matching method names while retaining independent algorithms is only an intermediate step.

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

If a model cannot satisfy an operation, expose a clear unsupported contract during integration rather than accepting and silently dropping behavior. The target adapter maps models and product context; it does not fork CRUD, ranking or lifecycle algorithms.

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

Acceptance for the subsequent migration is measured by deletion of duplicate host overrides and then duplicate general SQL logic, plus passing the checks above on both backends. A private adapter may remain, but must map product context rather than independently redefine memory behavior. Lifecycle work resumes only after its required shared storage guarantees and separate deletion contract are agreed; no retention policy is decided here.
