# Jev-Reranked Memory Retrieval

**Status:** Approved

**Date:** 2026-09-20

**Target:** memU `main`, as an opt-in integration with no default behavior change

## Summary

Add a Jev-powered second-stage relevance gate around memU's existing
`AgenticMemoryBackend` protocol. The existing backend continues to perform
embedding retrieval. The integration sends the returned segment and resource
candidates to TypeSafe Jev in one System One request, receives an independent
Noul probability for every candidate, filters and reorders the candidates, and
rolls the surviving segment scores back up to files.

The integration is additive. `MemoryService`, its three public operations,
storage repositories, database schemas, cloud transport, and default host CLI
behavior remain unchanged. Users enable Jev explicitly and install an optional
dependency. With the feature disabled, no Jev package is imported and no
memory content is sent to TypeSafe.

## Problem

memU currently retrieves memory with one query embedding and vector similarity.
That path is fast and portable, but semantic similarity alone cannot reliably
separate useful evidence from topical or lexical overlap. A query about a
current deployment procedure can therefore retrieve an old discussion that
mentions the same tools without containing an actionable answer.

Running a generative model over every retrieval would add seconds of latency,
unstructured output, and a new failure surface. Jev instead evaluates typed
questions about structured state and returns probabilities. TypeSafe reports a
70–500 ms service range for Jev-shaped calls, making a single batched relevance
evaluation suitable for memU's interactive retrieve path. This range is a
vendor report, not a latency guarantee; the implementation will measure and
publish observed warm p50 and p95 latency.

## Goals

- Make Jev materially responsible for the final memories returned to a caller.
- Use TypeSafe's real System One API through its official asynchronous Python
  SDK, not a prompt-compatible chat model or a local heuristic.
- Make at most one Jev inference request per retrieval.
- Work with any object satisfying `AgenticMemoryBackend`, including local
  `MemoryService` and `CloudMemoryClient`.
- Preserve current memU behavior and dependencies unless the integration is
  explicitly enabled.
- Preserve user scope filtering by delegating the first-stage retrieval to the
  configured backend without bypassing its `where` argument.
- Provide enough metadata to prove whether Jev was applied, fell back, or was
  skipped because there were no candidates.
- Include deterministic tests, a credential-gated live smoke test, and a
  repeatable latency benchmark.

## Non-Goals

- Replacing embeddings or vector indexes with Jev.
- Scanning an entire memory corpus through Jev.
- Changing the storage schema, repository protocols, or backend parity rules.
- Adding Jev calls to `MemoryService`; the core service remains embedding-only.
- Generating summaries, answers, or new memory content.
- Guaranteeing sub-100 ms or sub-second end-to-end latency across networks and
  embedding providers.
- Enabling Jev silently for existing installations.

## Considered Approaches

### 1. Protocol-level reranking wrapper — selected

Wrap any `AgenticMemoryBackend`. Delegate writes and listings unchanged. On
retrieval, call the wrapped backend, evaluate its bounded candidates with Jev,
and return the filtered and reordered result.

This keeps the integration outside the composition root, works for local and
cloud backends, and needs no schema or repository changes. It also makes the
Jev dependency optional and testable behind a small evaluator protocol.

### 2. Query routing only

Use Jev to decide which tracks or layers to search, then use the existing vector
ranking unchanged. This sends less memory content to TypeSafe, but Jev would not
judge the actual candidate memories and would provide little protection against
false-positive similarity hits.

### 3. Jev-only corpus scan

Send the whole memory corpus to Jev and use its answers as retrieval. This makes
Jev central, but latency, request size, privacy exposure, and cost grow with the
corpus. It also discards memU's existing indexed candidate generation. This
approach is rejected.

## Architecture

### Integration package

Create `memu.integrations.jev` containing these independent units:

- `JevRerankConfig`: validated model, threshold, timeout, candidate bound, and
  error-policy settings.
- `JevCandidate`: the minimal typed state sent for one segment or resource.
- `JevEvaluation`: model name, per-candidate probabilities, token usage, and
  measured provider latency.
- `JevEvaluator` protocol: one asynchronous `evaluate(query, candidates)` call.
- `TypeSafeJevEvaluator`: the production evaluator using
  `typesafe_sdk.AsyncTypeSafeClient` and Noul questions.
- `JevRerankedMemoryBackend`: an `AgenticMemoryBackend` wrapper that delegates
  listing and commit calls and applies Jev only to retrieval.

The production SDK import is lazy. Importing or running ordinary memU without
the `jev` extra must not require `typesafe-sdk`.

### Configuration and opt-in

Add an optional dependency:

```toml
[project.optional-dependencies]
jev = ["typesafe-sdk>=0.7.0,<0.8"]
```

The shared backend builder will wrap the selected local or cloud backend only
when `MEMU_RETRIEVAL_RERANKER=jev`. Configuration resolves through memU's
existing process-environment then `~/.memu/config.env` lookup:

| Setting | Default | Meaning |
| --- | --- | --- |
| `MEMU_RETRIEVAL_RERANKER` | unset | `jev` enables the wrapper |
| `TYPESAFE_API_KEY` | required when enabled | TypeSafe credential |
| `MEMU_JEV_MODEL` | `jev-latest` | TypeSafe model name or alias |
| `MEMU_JEV_MIN_RELEVANCE` | `0.5` | Minimum Noul probability kept |
| `MEMU_JEV_MAX_CANDIDATES` | `32` | Hard bound per Jev request |
| `MEMU_JEV_TIMEOUT_SECONDS` | `1.5` | Per-request SDK timeout |
| `MEMU_JEV_ON_ERROR` | `fallback` | `fallback` or `raise` |

The API key is passed explicitly from memU's config resolver to the SDK so host
adapters and scheduled tasks can read it from the same stable config file as
other settings. It is never logged or included in result metadata.

Developers can also construct `JevRerankedMemoryBackend` directly around a
custom backend and supply a custom evaluator or explicit configuration.

## Retrieval Data Flow

1. The wrapper calls `backend.progressive_retrieve(query, where=where)` exactly
   once. Scope validation and candidate generation remain the wrapped backend's
   responsibility.
2. It creates candidates from returned segments and resources:
   - segment state contains its `text`;
   - resource state contains its `caption`, falling back to its URL only when a
     caption is absent.
3. It merges both layers by descending original vector score, with layer and
   original position as stable tie-breakers, then truncates the combined list to
   `max_candidates`. Existing memU defaults produce ten candidates, below the
   proposed bound. Candidates beyond the bound are omitted from the Jev-shaped
   result rather than being returned without evaluation; metadata reports the
   number omitted.
4. If there are no candidates, the wrapper performs no Jev call and returns the
   original three layers plus metadata explaining the skip.
5. The evaluator sends one System One request. The shared state contains the
   query and the keyed candidate list. Each candidate receives one Noul
   question with explicit criteria:
   - true: the candidate contains concrete information directly useful for
     answering the query;
   - false: the candidate is irrelevant, only topically similar, or lacks
     information useful for the answer.
6. Jev returns one independent probability per candidate. The wrapper keeps
   candidates at or above `min_relevance`, orders them by Jev probability with
   the original vector score as a deterministic tie-breaker, and adds a
   `jev_score` field without overwriting the vector `score`.
7. Files are retained only when a surviving segment points to them. Their
   `jev_score` is the maximum score of their surviving segments, and they are
   ordered by that value.
8. The result keeps the existing `segments`, `files`, and `resources` keys and
   adds a `jev` metadata object containing applied/fallback status, resolved
   model, latency, token counts, candidate count, retained count, threshold,
   and truncation count.

When evaluation succeeds, this makes Jev authoritative over final inclusion and
ordering while preserving the original similarity score for inspection and
debugging. The explicit fallback policy is the only path that may return
unevaluated vector results while Jev is enabled.

## Error Handling

Configuration errors are always explicit: enabling Jev without the optional
package, an API key, or valid numeric settings raises before retrieval.

Runtime provider errors follow `MEMU_JEV_ON_ERROR`:

- `fallback` (default): return the untouched vector result plus `jev` metadata
  with `applied=false`, `fallback=true`, and the exception class. Do not include
  provider error messages because they may contain request details.
- `raise`: propagate the SDK exception so latency-sensitive or compliance-
  sensitive callers can refuse an unjudged result.

Malformed or incomplete Jev responses are runtime provider errors; they must
not be interpreted as zero relevance. Cancellation is never swallowed.

The SDK client is asynchronous and connection-reusing. The wrapper exposes
`aclose` and asynchronous context-manager methods for long-lived library use;
short-lived host CLI processes may rely on their normal process teardown.

## Privacy and Security

Enabling the feature sends the retrieval query and bounded candidate text to
TypeSafe. Documentation must state this immediately beside the opt-in steps.
The wrapper sends neither embeddings nor unrelated corpus rows. User scope data
is not added to the Jev state, although candidate content may itself contain
personal information.

The API key is read from configuration and passed directly to the official SDK.
Tests and logs must never print it. SDK request-body debug logging is not
enabled by the integration.

## Compatibility

- Default installs do not gain a new required dependency.
- Default backend construction returns the same concrete local or cloud object
  as before.
- `MemoryService` retains its existing implementation and three-entry-point
  public surface.
- No database migration or backend repository change is required.
- The opt-in wrapper satisfies `AgenticMemoryBackend` structurally.
- Existing result consumers that read the three documented layers continue to
  work; opt-in callers may additionally consume `jev` and `jev_score`.

## Testing

### Deterministic tests

- The wrapper delegates `list_all_recall_files` and `commit_results` exactly.
- Retrieval makes one evaluator call for segments and resources together.
- Returned state and Noul criteria identify the correct candidate.
- Thresholding, ordering, vector-score tie-breaking, and file roll-up are
  correct.
- Candidate bounding and truncation metadata are correct.
- Empty candidates do not call Jev.
- `fallback` preserves the vector result; `raise` propagates.
- `asyncio.CancelledError` propagates under both policies.
- Enabling without the optional dependency or API key fails clearly.
- The environment builder leaves default local/cloud objects untouched and
  wraps either backend only when explicitly configured.

Tests use an injected evaluator rather than mocking TypeSafe SDK internals.
Separate contract tests mock the SDK transport to pin the real System One
request and response shapes.

### Live smoke test

A test marked `integration` runs only when `TYPESAFE_API_KEY` is present. It
uses the official SDK against TypeSafe, supplies one relevant and one irrelevant
candidate, asserts probabilities are in `[0, 1]`, asserts the resolved model is
returned, and proves the call is Jev rather than a local fake. CI without the
credential skips it with an explicit reason.

### Benchmark

Add a credential-gated script that runs a deterministic in-memory memU backend
plus the real `TypeSafeJevEvaluator`. It performs warm-up calls, then reports:

- base retrieval latency;
- Jev provider latency;
- total retrieval latency;
- warm p50 and p95;
- candidate count and input-token usage.

The PR will report measured numbers from the available execution environment
and label them with region, date, model, and sample size. It will not convert a
small local run into a universal latency guarantee.

## Documentation

- Add an accepted ADR recording why Jev lives in an opt-in protocol wrapper
  instead of `MemoryService`.
- Add a README section with installation, configuration, privacy disclosure,
  result shape, fallback behavior, and a runnable example.
- Document how to run deterministic tests, the live smoke test, and the
  benchmark without placing a key on the command line.

## Delivery and PR Shape

The implementation will remain on `codex/jev-memory-reranker`, based directly
on upstream `main`. The design document is committed separately before code.
The implementation commit(s) will contain only the integration, configuration,
tests, benchmark, ADR, and user-facing documentation. No existing migration,
storage layout, or unrelated refactor is in scope.

## Acceptance Criteria

- Existing test suite and quality checks pass without the Jev extra enabled.
- The Jev-specific deterministic and transport-contract tests pass.
- A live credentialed run makes a real `jev-latest` call and returns calibrated
  candidate probabilities.
- One retrieval produces no more than one Jev inference request.
- With the feature disabled, existing retrieval output and behavior are
  unchanged.
- With the feature enabled, final segment/resource inclusion and ordering are
  determined by Jev probabilities, and file ordering follows surviving segment
  probabilities.
- Local and cloud backends can both be wrapped without changing their classes.
- No API key or candidate content appears in logs, exceptions created by memU,
  or committed fixtures.
