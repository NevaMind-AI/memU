# ADR 0019: Put Jev in an Optional Retrieval Wrapper, Not `MemoryService`

- Status: Accepted
- Date: 2026-09-21
- Builds on: ADR 0002, ADR 0005, ADR 0012

## Context

memU's interactive read path embeds a query, retrieves bounded segment and
resource candidates by vector similarity, and rolls segment hits up to files.
This is fast and portable, but vector similarity can rank topical overlap above
memory that directly answers the query.

TypeSafe Jev is a System One decision model. It accepts structured state and
typed questions and returns probabilities rather than generated text. A bounded
set of Noul relevance questions can therefore distinguish useful memory from
false-positive similarity hits in one request.

Putting that request inside `MemoryService` would violate two existing
boundaries. The service is intentionally embedding-only, and its three methods
work identically across pluggable storage backends. Jev also sends candidate
content to an external processor and adds an optional dependency, so it cannot
become a silent default.

## Decision

Implement Jev as `JevRerankedMemoryBackend`, a structural
`AgenticMemoryBackend` wrapper under `memu.integrations.jev`.

The wrapper delegates `list_all_recall_files` and `commit_results` unchanged.
For `progressive_retrieve`, it:

1. calls the configured local or cloud backend once;
2. merges the returned segment and resource candidates by vector score;
3. sends a bounded candidate set in one real Jev System One request, with one
   independent Noul relevance question per candidate;
4. filters and orders segments/resources by Jev probability; and
5. rolls surviving segment probabilities up to files.

The wrapper preserves the original vector `score`, adds `jev_score`, and emits a
small `jev` metadata object showing whether evaluation was applied or fell back.
It never changes storage, embeddings, or user-scope filtering.

The integration disables SDK retries so the one-call bound also means at most
one outbound System One HTTP attempt. Availability remains governed by the
wrapper's explicit fallback or raise policy instead of hidden retry latency.

The official asynchronous TypeSafe SDK is an optional `jev` package extra. The
shared backend builder installs the wrapper only when
`MEMU_RETRIEVAL_RERANKER=jev`. The default path does not import the SDK, require
a TypeSafe credential, change the backend object, or send memory content to
TypeSafe.

Runtime provider failures either return the untouched vector result with
explicit fallback metadata or raise, selected by configuration. Cancellation
always propagates. Configuration errors are never converted into fallback.

## Consequences

- `MemoryService` remains embedding-only and keeps its exact public surface.
- Local and cloud retrieval gain the same opt-in Jev behavior without storage
  backend changes or migrations.
- Jev is materially responsible for final inclusion and ordering when the
  evaluation succeeds, while the vector stage remains the scalable candidate
  generator.
- One retrieval makes no more than one Jev inference request.
- Enabling the integration sends the query and bounded candidate text to
  TypeSafe; documentation must disclose this beside the opt-in instructions.
- End-to-end latency gains one network decision call. Benchmarks report observed
  warm p50/p95 rather than treating TypeSafe's published range as a guarantee.
- The default fallback favors availability but is visibly distinguishable from
  a Jev-ranked response; strict callers can select the raise policy.
