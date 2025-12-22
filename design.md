Multimodal Memory Layer Framework — High-Level Design (Draft v0.2)
1. Background and Objectives
1.1 Background

This framework provides a multimodal, evolvable, and retrievable memory layer for AI applications. It transforms raw user uploads (conversations and files) into structured memory assets and continuously optimizes them over time.

1.2 Objectives

Four-layer memory unit hierarchy: Resource → Memory Item → Memory Category → Intention.

Three core flows: memorize / retrieve / evolve.

Pluggable capabilities:

Storage backends: in-memory by default, plus SQLite and Postgres (with primary support for pgvector).

Execution modes: synchronous by default; optional workflow orchestration via Temporal/Burr (public API unchanged).

Customizable steps: users can insert/replace default steps; step-level config overrides (e.g., per-step model profile) are supported.

Dynamic Scope:

Users provide a scope_model at service creation; the system provisions tables and indexes via dynamic DDL based on the scope columns.

The scope schema is fixed at initialization; mismatches later require user-driven migration/update.

The system does not generate an internal scope identifier; it uses user-provided scope columns directly (e.g., project_id/agent_id/...).

All public APIs require a scope; retrieve additionally supports cross-scope retrieval.

1.3 Non-goals (Current Phase)

No automatic scope migration when the scope schema changes.

SQLite does not aim to provide high-performance vector search; brute force is offered only as a lightweight use case.

The framework is not tied to a single LLM/embedding vendor; it prioritizes profile- and capability-based abstraction.

2. Key Concepts and Data Layers
2.1 Resource Layer

The source of truth for raw conversations and multimodal files.

Stores the content itself or a URI (e.g., object storage location), plus metadata, content hash, timestamps, etc.

Optional lightweight preprocessing artifacts: ASR/OCR/CAPTION and segmentation indices.

2.2 Memory Item Layer

Reusable memory points extracted and cleaned from Resources via LLM.

Must include evidence (traceable back to a resource fragment/page/timestamp, etc.), plus confidence, stability, and version info.

Optional embeddings for vector-based recall.

2.3 Memory Category Layer

Maps/aggregates memory items into a user-provided predefined taxonomy (categories).

Supports category summaries and anchors (representative items) for retrieval pruning and explanations.

2.4 Intention Layer

Captures global user intent, goals, constraints, and progress.

Acts as the top-level router for retrieval and links to categories/items.

3. Overall Architecture

The framework consists of three layers:

API Layer (Public Surface)

Exposes only: memorize(scope, ...), retrieve(scope_selector, ...), evolve(scope, ...).

A small set of read-only queries, e.g., list_categories(scope), get_category(scope, ...).

Workflow orchestration and internal step details are not exposed publicly.

Pipeline Layer (Business Orchestration)

Built-in default pipelines for memorize/retrieve/evolve.

A unified Step contract (step_id, role, requires/produces, capabilities).

Supports user patches to insert/replace/remove steps and override step configs.

Backend Layer (Pluggable Capabilities)

Metadata Store: transactional storage of resources/memories/relations/run logs (InMemory/SQLite/Postgres).

Vector Index: embedding write and similarity search (bruteforce/pgvector/future external stores).

Runner/Executor: Sync/Temporal/Burr for retries, timeouts, concurrency, and state persistence (transparent to public API).

4. Service Creation and Configuration Model
4.1 Expected Service Creation Interface

Users provide “foundation dependencies and domain configuration” at construction time, for example:

scope_model: a Pydantic model describing the scope schema (drives scope columns and dynamic DDL)

categories: a taxonomy category list (domain input)

llm_providers: a named profile dictionary with default and optional additional profiles (referenced by steps)

storage_providers: metadata store configuration (required) and optional vector index configuration (may be inferred)

4.2 LLM Providers: Named Profile Mechanism

llm_providers is defined as profiles, not “multiple client instances.”

Must include the default profile.

Each profile defines model/deployment, credential references, temperature, token budget, timeout, retry policy, structured-output modes, etc.

Each pipeline step references a profile by name (e.g., profile_a); profiles are managed centrally for reuse and auditability.

Config override precedence (recommended)

step-level explicit profile

pipeline/role default profile mapping

default

4.3 Storage Providers: Capability Splitting and Composition

metadata_store (required): provider (memory/sqlite/postgres), connection info, ddl_mode (create/validate)

vector_index (optional): bruteforce/pgvector/none

Can be inferred from metadata_store, but inference results must be recorded in metadata for reproducibility.

5. Scope Design and Dynamic DDL
5.1 Core Decisions

Scope fields are determined and locked by the user-provided scope_model at service creation time.

The system does not generate an internal scope identifier; it uses the scope columns directly for isolation.

All public APIs require scope input; write paths require a fully specified scope.

5.2 Dynamic DDL (Provisioning Phase)

At creation time the service provisions schema:

Creates scope columns (based on scope_model field names and order) for all core tables.

Creates composite indexes with scope columns as the prefix.

Writes service_meta: scope_schema_hash, scope_fields, ddl_version, taxonomy_version, and a redacted provider-config summary.

Scope mismatch handling (finalized):

If a runtime scope input is missing fields or does not match the stored schema, reject the request and require user-driven migration/rebuild.

6. Public API Design
6.1 The Three Core Functions

memorize(scope, resource|conversation, options?)

Writes the resource and builds/stores items/categories/intentions.

Idempotency/versioning: recommended internally via resource hash + pipeline version (not necessarily exposed publicly).

retrieve(scope_selector, query, options?)

Supports cross-scope retrieval (see Section 7).

Hierarchical retrieval: intention → category → item; each layer can run an LLM “sufficiency check,” descending only if needed.

Supports embedding search and pure-LLM judgment with graceful fallback.

evolve(scope, options?)

Background evolution: supplement/deduplicate items, re-cluster categories, adjust intentions.

Can be triggered externally or scheduled internally (runner-dependent; API unchanged).

6.2 Read-only Queries (Simple Store Queries)

list_categories(scope, include_summary, include_items=...)

get_category(scope, category_key_or_id, ...)

Optional: get_latest_intention(scope)

7. Cross-Scope Retrieval (ScopeSelector and Policy Constraints)
7.1 ScopeSelector Semantics

retrieve still requires scope input, but allows cross-scope expression:

Exact: project_id = "p1"

Multi-value: project_id IN ["p1", "p2"]

Wildcard: ANY (cross that column)

7.2 Cross-scope Policy (Mandatory Boundary and Cost Controls)

To prevent unbounded full-dataset scans and potential unauthorized access, the service enforces cross-scope policies (defaulted or configurable):

Boundary fields must be specified: at least one boundary field must be exact or multi-value; ANY is forbidden (e.g., organization_id or project_id).

Max scope combinations: cap on expanded combinations from IN.

Max candidate limits: caps on vector recall top-k and LLM rerank candidate set sizes.

Fallback strategy: if vector capability is unavailable or the scope range is too large, degrade to intention/category routing and narrow LLM judgments.

Recommended finalization: even with dynamic scope, require boundary field declaration at creation time; otherwise cross-scope retrieval cannot be constrained safely.

8. Pipeline Design and Customization
8.1 Default Pipelines (High-level Steps)

Memorize (illustrative)

ingest_resource → preprocess_multimodal (optional) → extract_items → dedupe_merge → categorize_items → infer_intention → persist/index

Retrieve (illustrative)

route_intention → sufficiency_check → route_category → sufficiency_check → recall_items (vector/rules) → verify_rerank (LLM) → build_context

Evolve (illustrative)

select_targets → refresh_items → re_cluster_categories → adjust_intention → persist/index → emit_diff

8.2 Step Contract (Required)

Each step (built-in or user-defined) must define:

step_id: stable identifier for configuration and patching

role: used for default profile mapping and governance (extract/cluster/verify/route, etc.)

requires/produces: declared dependencies on pipeline state

capabilities: whether the step requires LLM, vector search, or DB writes

8.3 Pipeline Editing Interfaces (User-facing Control)

The framework exposes simple pipeline control methods (without exposing the DAG engine):

service.config(step_id, configs): override step config (e.g., llm_profile, thresholds, top_k, template version)

service.insert_after(step_id, new_step)

Recommended additions: insert_before / replace / remove(or disable)

8.4 Two Mandatory Guardrails (Maintainability)

Validate on change: any config/patch must trigger static validation (dependencies, profile existence, capability availability). If invalid, reject the change.

Snapshot on change: each accepted change produces a new pipeline revision for auditability, reproducibility, and rollback.

9. Execution Modes (Sync / Temporal / Burr) Are Transparent

Default synchronous execution: steps run sequentially within one process.

Optional workflow engines: Temporal/Burr act only as runners/executors providing:

step-level retries, timeouts, concurrency control

state persistence and failure recovery (if supported)

run logging

Public API and semantics remain consistent across runners.

10. Data and Version Governance
10.1 Versioning and Reproducibility

Track at least:

scope_schema_hash

taxonomy_version (hash/version of categories)

pipeline_revision (step topology + step configs)

10.2 Run Logging (Recommended Internal Capability)

Maintain run records for memorize/retrieve/evolve: input summary, scope range, step timings, LLM usage, failure causes, output summary. This is especially important for Temporal/Burr-based execution.

11. Storage Backends and Vector Strategy
11.1 InMemory (Default)

Suitable for tests and rapid validation.

Brute-force vector search is acceptable.

11.2 SQLite

Suitable for lightweight local persistence.

Vector search is brute force only (explicitly “functional,” not “performance-grade”).

11.3 Postgres + pgvector (Primary Production Path)

Provides transactional integrity and concurrency.

Composite scope indexes.

Vector indexes (HNSW/IVFFLAT) for efficient Top-K retrieval.

11.4 Preserved Extension Points

VectorIndex can be swapped for external vector stores without changing pipelines or public APIs.

12. Security and Isolation (Future Multi-tenant Readiness)

Every read/write is scope-filtered; cross-scope retrieval must be constrained by policy.

Consider a pluggable authorization layer before scope-selector expansion to prevent cross-project/tenant data leakage.

Secrets (e.g., API keys) should be referenced (env/secret manager), not stored in plaintext.

13. MVP Recommendations (Aligned with Current Tradeoffs)

Dynamic DDL: support create/validate; no scope migration.

LLM profiles: support default + additional profiles; step-level overrides.

Taxonomy: categories required; implement mapping + summaries first; clustering can be enhanced later.

SQLite: brute-force vector recall only; optimize Postgres+pgvector as the main path.

Pipeline editing: implement config + insert_after + replace initially, with validation + revision snapshots.
