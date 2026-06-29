# AGENTS.md

Operational guide for AI coding agents working in this repository.

## Mission

Ship small, verified feature and bugfix changes while preserving memU's current architecture.
Treat `docs/architecture.md` as the runtime source of truth and keep this file aligned with it.

Core invariants:

- `MemoryService` is the composition root for config, storage, LLM/VLM/embedding clients, workflows, interceptors, and memory file export.
- Public APIs should remain stable unless the requested change explicitly requires an API change.
- Major behavior runs through workflows: `memorize`, `retrieve_rag`, `retrieve_llm`, and CRUD/patch operations.
- Workflow steps must keep explicit `requires`/`produces` contracts and declared capability tags.
- Storage is pluggable across `inmemory`, `sqlite`, and `postgres`; repository contract changes require backend parity.
- Scope data comes from `UserConfig.model`; validate `where` filters and do not bypass scope filtering.
- LLM routing is profile-based across chat, embedding, VLM, and custom profiles.
- The exported memory workspace should stay human-readable and agent-traversable: `INDEX.md`, `MEMORY.md`, `memory/`, `resource/`, and `skill/`.

## First Move

Before editing, classify the request by the layer it touches:

- Service/runtime wiring: `src/memu/app/service.py`
- Memorize pipeline: `src/memu/app/memorize.py`
- Retrieve pipelines: `src/memu/app/retrieve.py`
- CRUD/patch behavior: `src/memu/app/crud.py`
- Config models/defaults: `src/memu/app/settings.py`
- Workflow engine and pipeline mutation: `src/memu/workflow/*`
- Memory file export/synthesis: `src/memu/app/memory_files.py`, `src/memu/memory_fs/*`, `src/memu/prompts/memory_fs*`
- Storage protocols/factory: `src/memu/database/interfaces.py`, `src/memu/database/factory.py`
- In-memory backend: `src/memu/database/inmemory/*`
- SQLite backend: `src/memu/database/sqlite/*`
- Postgres backend: `src/memu/database/postgres/*`
- Vector math/ranking: `src/memu/vector.py`
- LLM clients, wrappers, interceptors: `src/memu/llm/*`
- Embedding clients: `src/memu/embedding/*`
- Vision clients: `src/memu/vlm/*`
- Integrations/client surfaces: `src/memu/integrations/*`, `src/memu/client/*`
- Tests: `tests/*`
- User-facing docs/examples: `README.md`, `readme/*`, `docs/*`, `examples/*`

Read the relevant implementation and nearby tests first. Prefer local patterns over new abstractions.

## Implementation Rules

- Keep changes narrow and localized to the affected layer.
- Preserve async behavior and avoid sync work in async paths unless existing code already does it.
- Prefer adding or modifying a workflow step over embedding new flow logic directly in `MemoryService`.
- When adding configurable behavior, update typed settings and wire it through step config or service config.
- Preserve result shapes unless the task explicitly asks for a breaking change.
- Maintain type hints and mypy compatibility.
- Keep provider-specific logic inside provider/backend modules.
- Keep storage-neutral logic outside concrete backends; vector ranking helpers belong in shared modules such as `memu.vector`.
- Do not duplicate client caching. Use the existing client pool/profile routing patterns.
- Do not silently swallow errors that should be visible to callers or tests.
- Avoid broad refactors unless they are required to make the requested change safe.

## Workflow Guidance

For memorize work:

- Keep modality routing in the preprocessing pipeline.
- Use VLM clients for image/video paths and chat clients for conversation/document/audio paths.
- Preserve the flow: ingest resource, preprocess, extract items, dedupe/merge, categorize, persist index, build response.
- If rich document ingestion changes, consider the optional `document` extra and MarkItDown behavior.

For retrieve work:

- Check both `retrieve_rag` and `retrieve_llm` when behavior is shared.
- Validate `where` filters against the configured user model before querying.
- Keep category, item, and resource recall responsibilities separated.
- Preserve early-stop/sufficiency behavior when modifying ranking or response build steps.

For CRUD/patch work:

- Respect repository contracts and scope fields.
- Preserve existing output shapes for list/create/update/delete operations.
- Add backend coverage when contracts change.

For memory file export:

- Keep raw resources copied verbatim into `resource/`.
- Keep category memory split under `memory/<slug>.md`.
- Keep synthesized skills under `skill/<name>/SKILL.md`.
- Keep root files as indexes/overviews, not hidden sources of untracked state.
- Treat synthesized skill output as derived from source descriptions, not from unrelated runtime state.

## Backend Parity

If a repository method, model field, filter behavior, or vector search contract changes:

1. Update the protocol/interface.
2. Update `inmemory`, `sqlite`, and `postgres` implementations where applicable.
3. Add or extend conformance tests.
4. Check migrations/bootstrap behavior for SQL backends.
5. Verify fallback behavior when pgvector or optional extras are unavailable.

## LLM, VLM, And Embedding Routing

- Chat-like work uses LLM profiles.
- Embedding work uses embedding profiles and dedicated embedding clients.
- Image/video understanding uses VLM clients derived from LLM profiles unless explicitly configured otherwise.
- Step config should select profiles with existing keys such as `llm_profile`, `chat_llm_profile`, and `embed_llm_profile`.
- Keep interceptors and usage metadata behavior consistent across capabilities.
- Do not add embeddings back into chat clients; embedding is intentionally decoupled.

## Feature Checklist

1. Locate the affected flow, backend, integration, or export path.
2. Update settings/defaults only if behavior is configurable.
3. Wire the change through `MemoryService`, pipeline registration, or step config as appropriate.
4. Implement repository/backend changes for all impacted providers.
5. Add focused tests for the happy path and edge cases.
6. Update docs/examples for user-visible behavior.
7. Add or update ADRs under `docs/adr/` for architectural changes.

## Bug Fix Checklist

1. Reproduce the bug with an existing or new failing test.
2. Fix the smallest correct layer.
3. Add a regression test that fails before and passes after.
4. Check cross-backend effects when storage behavior changes.
5. Check both retrieval modes when recall/ranking/response behavior changes.
6. Confirm no unintended public API or output-shape changes.

## Testing And Validation

Use `uv` for local runs.

- Setup: `make install`
- Run all tests: `make test`
- Run focused tests: `uv run python -m pytest tests/<target_test>.py`
- Full quality checks: `make check`

At minimum, run targeted tests for touched code. Run `make check` for broad, cross-cutting, or release-critical changes.
If a required check cannot be run, say why in the final summary.

Useful focused areas:

- Storage parity: `tests/test_backend_conformance.py`, `tests/test_inmemory.py`, `tests/test_sqlite.py`, `tests/test_postgres.py`
- Retrieval/vector behavior: `tests/test_vector.py`, `tests/test_salience.py`, retrieve-related tests
- Multimodal preprocessing: `tests/test_conversation_preprocess.py`, `tests/test_document_text.py`, `tests/test_audio_preprocess.py`, `tests/test_vlm_preprocess.py`
- Memory file export/synthesis: `tests/test_memory_files.py`, `tests/test_memory_fs_synthesis.py`
- Provider routing: `tests/test_embedding.py`, `tests/test_openrouter.py`, `tests/test_openai_max_tokens.py`, `tests/test_lazyllm.py`
- Integrations/tool memory: `tests/test_tool_memory.py`, LangGraph-related tests

## Documentation Rules

- Update `README.md`, localized `readme/*`, `docs/*`, or examples when behavior visible to users changes.
- Keep architecture docs current when composition, workflow contracts, backends, or profile routing changes.
- Keep examples runnable and aligned with the public API.
- Do not document speculative features as implemented.

## Done Criteria

Before finishing:

- Code compiles for touched paths.
- Tests for changed behavior pass.
- New behavior has test coverage.
- User-visible or architectural behavior is documented.
- Backend parity has been considered and implemented where needed.
- No unrelated files were modified.
