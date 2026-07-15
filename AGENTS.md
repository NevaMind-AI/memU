# AGENTS.md

Operational guide for AI coding agents working in this repository.

## Mission

Ship small, verified feature and bugfix changes while preserving memU's current architecture.

Core invariants:

- `MemoryService` (`src/memu/app/service.py`) is the composition root: config, storage, and the embedding client pool. Its public surface is exactly the three `AgenticMixin` entry points — `list_all_recall_files`, `progressive_retrieve`, `commit_results`.
- memU is embedding-only. No LLM/chat call happens anywhere in the service; do not add one.
- Storage is pluggable across `inmemory`, `sqlite`, and `postgres`; repository contract changes require backend parity.
- Scope data comes from `UserConfig.model`; validate `where` filters (`_normalize_where`) and do not bypass scope filtering.
- Retrieval config lives in `ProgressiveRetrieveConfig` (`file` + `resource` layers); embedding profiles in `EmbeddingProfilesConfig`.

## Layer Map

- Service + three entry points: `src/memu/app/service.py`, `src/memu/app/agentic.py`
- Config models/defaults: `src/memu/app/settings.py`
- Storage protocols/factory: `src/memu/database/interfaces.py`, `src/memu/database/factory.py`
- Backends: `src/memu/database/{inmemory,sqlite,postgres}/*`
- Vector math/ranking: `src/memu/vector.py`
- Embedding clients: `src/memu/embedding/*`
- CLI (`memu`): `src/memu/cli.py`; shared `MEMU_*` config: `src/memu/env.py`
- Host adapters (`memu-codex`, bridging pipeline): `src/memu/hosts/*`
- Tests: `tests/*`

Read the relevant implementation and nearby tests first. Prefer local patterns over new abstractions.

## Implementation Rules

- Keep changes narrow and localized to the affected layer.
- Preserve async behavior and result shapes unless the task explicitly asks for a breaking change.
- Maintain type hints and mypy compatibility.
- Keep provider-specific logic inside `memu.embedding.backends`; storage-neutral logic outside concrete backends.
- Do not duplicate client caching — use the existing `ClientPool` pattern.
- Do not silently swallow errors that should be visible to callers or tests.

## Backend Parity

If a repository method, model field, filter behavior, or vector search contract changes:

1. Update the protocol in `src/memu/database/repositories/`.
2. Update `inmemory`, `sqlite`, and `postgres` implementations where applicable.
3. Extend `tests/test_agentic.py` (runs against inmemory + sqlite).
4. Check migrations/bootstrap behavior for SQL backends (`src/memu/database/postgres/migrations/`).

## Testing And Validation

Use `uv` for local runs.

- Setup: `make install`
- Run all tests: `make test`
- Run focused tests: `uv run python -m pytest tests/<target_test>.py`
- Full quality checks: `make check`

Useful focused areas:

- The three entry points end-to-end: `tests/test_agentic.py`
- Vector ranking: `tests/test_vector.py`
- Embedding providers/gateway: `tests/test_embedding.py`
- CLI surface: `tests/test_cli.py`
- Host adapter inject seam: `tests/test_host_instruction.py`

## Documentation Rules

- Update `README.md` or `npm/README.md` when user-visible behavior changes.
- Add or update ADRs under `docs/adr/` for architectural changes; existing ADRs are historical records — do not rewrite them.
- Do not document speculative features as implemented.

## Done Criteria

- Code compiles for touched paths; tests for changed behavior pass.
- New behavior has test coverage.
- Backend parity considered and implemented where needed.
- No unrelated files modified.
