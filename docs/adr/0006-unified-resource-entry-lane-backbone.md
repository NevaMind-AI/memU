# ADR 0006: Unify INDEX / MEMORY / SKILL onto a Resource + Entry Lane Backbone

- Status: Proposed
- Date: 2026-06-25

## Context

memU historically modeled structured memory as four record types — `Resource`,
`MemoryItem`, `MemoryCategory`, `CategoryItem` — with retrieval running a fixed
`category -> item -> resource` waterfall. Separately, the read-only `memory_fs`
exporter projected three markdown trees (`INDEX.md`, `MEMORY.md`, `SKILL.md`)
that were decoupled from retrieval, and skills were handled by an ad-hoc dual
track (`memory_type="skill"` items *or* LLM synthesis).

This produced three asymmetric concepts:

- INDEX: `Resource.caption` + verbatim `resource/` copies
- MEMORY: `MemoryCategory.summary` + `memory/<slug>.md`
- SKILL: synthesized or bypassed, not part of retrieval

We want INDEX, MEMORY, and SKILL to share **one backbone** with **consistent
storage and retrieval**, all derived from the same per-resource canonical text.

## Decision

Collapse the model to **two first-class, lane-tagged entities plus one edge**.

### Lane

A `lane` discriminator with three values: `index`, `memory`, `skill`. (Raw
inputs use `lane="source"`.) The three lanes are parallel, structurally
identical processing tracks over a shared trunk; they differ only in *what the
extractor pulls out* and *the entry→resource grouping cardinality*.

### Entities

1. **`Resource`** (lane-tagged, one physical table — "everything is a resource"):
   - Raw source artifacts (`lane="source"`, `modality` = video/image/audio/
     conversation/document); multimodal preprocessing fills `content` (the
     canonical, modality-agnostic text — the shared trunk).
   - Generated coarse docs (`lane` ∈ {index, memory, skill}, `modality="markdown"`),
     each rendered as a file under the `resource/` root:
     - `resource/index/<slug>.md` — a description page linking to a raw resource
     - `resource/memory/<slug>.md` — a category page
     - `resource/skill/<slug>.md` — a skill page
   - Carries `embedding` (for coarse recall) and `resource_refs` provenance back
     to the raw sources it derives from.
   - This **absorbs the former `MemoryCategory`** (a category is just a
     `lane="memory"` markdown resource).

2. **`Entry`** (lane-tagged, one physical table — the searchable atom):
   - index → a resource description; memory → a memory item; skill → a reusable
     operation step.
   - Carries `text`, `embedding`, `entry_kind` (memory sub-type / step kind),
     `extra`, and `source_path` — a back-link to the originating raw resource,
     relative to the `resource/` root. (This **generalizes the former
     `MemoryItem`**.)

3. **`ResourceEntry`** (edge): membership of an `Entry` in its coarse lane
   `Resource` (memory item ∈ category page, skill step ∈ skill page, description
   ∈ index page). Many-to-many. (This **generalizes the former `CategoryItem`**.)

### Links / provenance

- `Entry.source_path` points only at the originating raw resource (relative to
  the `resource/` root).
- A coarse `Resource`'s provenance (`resource_refs`) is the union of its member
  entries' sources, stored redundantly to avoid a query-time join.
- All paths are relative to the single `resource/` root, so the same value works
  for both the retrieval API and the exported tree.

### Pipelines

- **memorize**: `ingest -> preprocess_multimodal (-> Resource.content) ->
  extract_lanes (index/memory/skill extractors) -> embed_entries ->
  persist lane resources -> build_response`.
- **retrieve**: for each enabled lane, `Resource` recall (stored embedding,
  `where lane=`) → `Entry` recall (stored embedding, `where lane=`), returning a
  per-lane shape `{index: {...}, memory: {...}, skill: {...}, resources: [...]}`.
  All lanes traverse the same code path; only the `lane` filter differs.

### Naming

`lane`, `Resource`, `Entry`, `ResourceEntry`, `content` (canonical text),
`source_path`, `resource_refs`. The former `Doc`/`LaneDoc` concept is dropped:
a "doc" is just a markdown `Resource`, which avoids mislabeling a video/image as
a document.

## Consequences

Positive:

- One storage schema and one retrieval path for all three lanes (true
  storage/retrieval consistency).
- Skills become first-class and searchable; the dual-track synthesis/bypass goes
  away.
- Every entry and coarse resource is traceable back to its raw source.
- "Everything is a resource" keeps the mental model and the on-disk tree aligned.

Negative / risk:

- Breaking schema change: `MemoryCategory` folds into `Resource`; `MemoryItem` →
  `Entry`; `CategoryItem` → `ResourceEntry` (field renames included). All three
  backends (`inmemory`, `sqlite`, `postgres`) and the app layer (`memorize`,
  `retrieve`, `crud`) must be migrated together.
- `retrieve` is category-centric today and needs a substantial rewrite.
- Stored vs query-time category embeddings are unified onto stored embeddings,
  changing recall behavior slightly.
