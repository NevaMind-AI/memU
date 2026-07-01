# ADR 0004: Add Workspace Memorize Without Touching Single-File `memorize`

- Status: Accepted
- Date: 2026-06-22

## Context

A feature branch (`feat/memory-fs-synthesis`) added a markdown "memory file system"
export, LLM synthesis of `MEMORY.md`/`SKILL.md`, an incremental update path, an
embedding-decoupling refactor, and a folder/workspace memorize entry point.

In its original arrangement that work mutates the existing single-file
`memorize(resource_url, modality)` entry point — and ultimately rewrites it to
take a `folder` argument. We want the existing `memorize` contract to stay
untouched and to introduce the directory behavior as a new, additive entry point
instead.

## Decision

Land the work as seven new, re-scoped commits:

1. **Folder backbone** — add `blob/folder.py` (scan / manifest / diff) and a new
   `memorize_workspace(folder)` entry that diff-syncs a directory
   (add/modify/delete with cascade-delete of stale memory) by looping over the
   **unchanged** `memorize`. No export yet.
2. **Export** — add the memory-file-system export and wire a best-effort full
   re-export into `memorize_workspace`.
3. **Synthesis + update path** — add LLM synthesis of `MEMORY.md`/`SKILL.md` and
   the stateful initialize-vs-incremental-update path. The update-on-memorize hook
   attaches to `memorize_workspace`, not `memorize`.
4. **Finish `skill/` decoupling** in `memory_fs`: the `skill/` tree is always
   synthesized from descriptions, never derived from extracted skill-type memory
   items. (Unblocks the step-5 restructure.)
5. **Export-tree restructure** — restructure the export tree into `resource/` /
   `memory/` / `skill/` with root indexes (`INDEX.md`/`MEMORY.md`/`SKILL.md`) and
   bytes-aware diffing. Only the directory restructure is taken; `skill/` stays
   synthesized from descriptions (the step-4 design), so the
   synthesizer/`_build_memory_files` stay as they were and only `exporter.py` is
   reworked.
6. **Flow + protocol cleanup** — split the oversized flows
   (`retrieve_llm.py` / `memorize_parse.py`), narrow the `Database` protocol to
   repositories only, and remove the Rust scaffolding.
7. **Decouple embedding** — route vectorization through the dedicated
   `memu.embedding` clients and drop `embed()` from the chat clients. Kept strictly
   last and isolated so it is independently revertable.

`memorize(resource_url, modality)` remains byte-for-byte unchanged throughout.

Embedding can be last because the decouple only swaps the implementation behind
already-stable call sites (`_get_step_embedding_client` / `.embed()`); nothing in
steps 1–6 depends on the new embedding clients.

## Notes

- The export, synthesizer, and update-path work do not touch `memorize`, so those
  steps are clean. Only the initialize-vs-update hook is relocated from `memorize`
  to `memorize_workspace`.
- The source branch oscillated on where `skill/` content comes from — first
  decoupling it to LLM synthesis, then re-coupling it to extracted skill-type
  memory items. We keep the synthesis design (step 4) and take only the directory
  restructure (step 5), so `exporter.py` is reworked by hand rather than applied
  wholesale.
- Cleanup concerns that were originally bundled together are split so the embedding
  decouple lands alone in step 7, isolated and easy to revert.

## Consequences

Positive:

- existing `memorize` callers are unaffected; directory ingestion is purely additive
- embedding decoupling is isolated in its own commit (step 7) and easy to revert
- each new commit is independently reviewable

Negative:

- the work is split and reordered relative to the source branch, so the new history
  is a re-scoped reconstruction rather than a replay of it
- `memorize_workspace` and `memorize` share the single-file core but are separate
  entry points to maintain
