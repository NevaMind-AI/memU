# AGENTS.md

Guidance for AI coding agents working in this repository.

## Goal

Implement features and fix bugs with minimal regression risk, while preserving memU's architecture:

- `MemoryService` as composition root
- workflow-based execution (`memorize`, `retrieve`, CRUD/patch)
- pluggable storage backends (`inmemory`, `sqlite`, `postgres`)
- profile-based LLM routing (`default`, `embedding`, custom profiles)

See `docs/architecture.md` for the current architectural view.

## Where to Change Code

- Service/runtime wiring: `src/memu/app/service.py`
- Memorize flow: `src/memu/app/memorize.py`
- Retrieve flow: `src/memu/app/retrieve.py`
- CRUD/Patch flow: `src/memu/app/crud.py`
- Config models/defaults: `src/memu/app/settings.py`
- Workflow engine: `src/memu/workflow/*`
- Storage abstraction/factory: `src/memu/database/interfaces.py`, `src/memu/database/factory.py`
- In-memory: `src/memu/database/inmemory/*`
- SQLite: `src/memu/database/sqlite/*`
- Postgres: `src/memu/database/postgres/*`
- LLM clients/wrappers/interceptors: `src/memu/llm/*`
- Integrations: `src/memu/integrations/*`, `src/memu/client/*`
- Tests: `tests/*`

## Implementation Rules

- Keep changes small and localized.
- Do not change public API signatures unless explicitly required.
- Preserve async behavior and existing workflow step contracts (`requires`/`produces` keys).
- If adding a new capability, prefer integrating through an existing pipeline step or a new clearly named step.
- Maintain backend parity where appropriate (if a repository contract changes, update all relevant backends).
- Validate `where`/scope behavior against `UserConfig.model`; do not bypass scope filtering.
- Keep type hints and mypy compatibility intact.

## Feature Work Checklist

1. Locate affected flow(s): memorize, retrieve, CRUD, or integration layer.
2. Update config models/defaults if behavior is configurable.
3. Wire behavior through `MemoryService` pipelines and step config (LLM profiles/capabilities).
4. Implement backend/repository changes for all impacted providers.
5. Add/extend tests for happy path and edge cases.
6. Update docs when behavior changes (`README.md`, `docs/*`, examples if needed).
7. If the change is architectural, add/update ADRs under `docs/adr/`.

## Bug Fix Checklist

1. Reproduce with an existing or new failing test.
2. Implement the smallest safe fix at the correct layer.
3. Add a regression test that fails before and passes after.
4. Check cross-backend effects (`inmemory`, `sqlite`, `postgres`) and retrieval modes (`rag`, `llm`) when relevant.
5. Verify no unintended API/output shape changes.

## Testing and Validation

Use `uv` for all local runs.

- Setup: `make install`
- Run all tests: `make test`
- Run focused tests: `uv run python -m pytest tests/<target_test>.py`
- Full quality checks: `make check`

At minimum, run targeted tests for touched code. Run `make check` for broad or cross-cutting changes.
If you cannot run a required check, state it explicitly in your final summary.

## Done Criteria

Before finishing, ensure:

- Code compiles and tests for changed behavior pass.
- New behavior is covered by tests.
- Docs are updated for user-visible or architectural changes.
- No unrelated files were modified.
