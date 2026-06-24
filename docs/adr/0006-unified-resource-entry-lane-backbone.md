# ADR 0006: Unify INDEX / MEMORY / SKILL onto a Resource + Entry Lane Backbone

- Status: Accepted
- Date: 2026-06-25

## Context

memU historically modeled structured memory as four record types — `Resource`,
`MemoryItem`, `MemoryCategory`, `CategoryItem` — with retrieval running a fixed
`category -> item -> resource` waterfall. Separately, the read-only `memory_fs`
exporter projected markdown trees that were decoupled from retrieval.

This produced asymmetric concepts:

- INDEX: `Resource.caption` + verbatim `resource/` copies
- MEMORY: `MemoryCategory.summary` + `memory/<slug>.md`

We want INDEX, MEMORY, and SKILL to share **one backbone** with **consistent
storage and retrieval**, all derived from the same per-resource canonical text.
Each lane is the same processing track; lanes differ only in their entry-type
set, extraction prompts, and how entries are grouped into coarse lane docs.

## Decision

Collapse the model to **two first-class, lane-tagged entities plus one edge**.

### Lane

A `lane` discriminator: `index`, `memory`, and `skill`. (Raw inputs use
`lane="source"`.) The lanes are parallel, structurally identical processing
tracks over a shared trunk; they differ only in *what the extractor pulls out*
(per-lane `entry_type` set and prompts) and *the entry→resource grouping
cardinality*:

- `index` — `entry_type` ∈ {`description`}, **`per_resource`** grouping: one
  coarse description doc per source resource (1:1, no LLM grouping).
- `memory` — `entry_type` ∈ {`profile`, `event`, `knowledge`}, **`adaptive`**
  grouping: the extractor proposes group names and a summarized category doc is
  synthesized per group.
- `skill` — `entry_type` ∈ {`tool`, `log`}, **`adaptive`** grouping: entries are
  grouped into summarized skill docs (analogous to memory categories).

Per-lane behavior is configured via `MemorizeConfig.lanes` (a `dict[str,
LaneConfig]`); all three lanes are enabled by default. Each adaptive lane has its
own summary prompt / target length / LLM profile.

### Entities

1. **`Resource`** (lane-tagged, one physical table — "everything is a resource"):
   - Raw source artifacts (`lane="source"`, `modality` = video/image/audio/
     conversation/document); multimodal preprocessing fills `content` (the
     canonical, modality-agnostic text — the shared trunk).
   - Generated coarse docs (`lane` ∈ {index, memory, skill},
     `modality="markdown"`), each rendered as a file under the `resource/` root:
     - `resource/index/<slug>.md` — a description page linking to a raw resource
     - `resource/memory/<slug>.md` — a category page
     - `resource/skill/<slug>.md` — a skill page
   - Carries `embedding` (for coarse recall) and `resource_refs` provenance back
     to the raw sources it derives from.
   - This **absorbs the former `MemoryCategory`** (a category is just a
     `lane="memory"` markdown resource).

2. **`Entry`** (lane-tagged, one physical table — the searchable atom):
   - index → a resource description; memory → a memory item; skill → a tool/log.
   - Carries `text`, `embedding`, `entry_type` (the per-lane sub-type, which
     selects the extraction prompt), `extra`, and `source_path` — a back-link to
     the originating raw resource, relative to the `resource/` root. (This
     **generalizes the former `MemoryItem`**.)

3. **`ResourceEntry`** (edge): membership of an `Entry` in its coarse lane
   `Resource` (memory item ∈ category page, description ∈ index page, tool/log ∈
   skill page). Many-to-many. (This **generalizes the former `CategoryItem`**.)

### Links / provenance

- `Entry.source_path` points only at the originating raw resource (relative to
  the `resource/` root).
- A coarse `Resource`'s provenance (`resource_refs`) is the union of its member
  entries' sources, stored redundantly to avoid a query-time join.
- All paths are relative to the single `resource/` root, so the same value works
  for both the retrieval API and the exported tree.

### Pipelines

- **memorize**: `ingest -> preprocess_multimodal (-> Resource.content) ->
  extract_lanes (per enabled lane: index/memory/skill extractors) ->
  embed_entries -> persist lane resources (per_resource 1:1 doc or adaptive
  grouped+summarized docs) -> build_response`.
- **retrieve**: a single `route_intention` pass, then for each enabled lane,
  `Resource` recall (stored embedding, `where lane=`) → `Entry` recall (stored
  embedding, `where lane=`), plus a `source`-lane resource recall, returning a
  per-lane shape `{lanes: {index, memory, skill}, resources: [...]}` (with
  backward-compatible top-level `categories`/`items` mirroring the memory lane).
  All lanes traverse the same code path; only the `lane` filter differs. Both
  `rag` and `llm` ranking methods are supported.

### Naming

`lane`, `Resource`, `Entry`, `ResourceEntry`, `content` (canonical text),
`source_path`, `resource_refs`. The former `Doc`/`LaneDoc` concept is dropped:
a "doc" is just a markdown `Resource`, which avoids mislabeling a video/image as
a document.

## Consequences

Positive:

- One storage schema and one retrieval path for all lanes (true
  storage/retrieval consistency).
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
