ADR 0007: Split Memorize/Retrieve into Three Independent Lines on a Layered Kernel

- Status: Proposed
- Date: 2026-07-01
- Supersedes: ADR 0004 (workspace memorize + memory file system), ADR 0006 (skill as a `RecallFile` track)

## Context

ADR 0004 added `memorize_workspace`/the markdown memory file system; ADR 0006 promoted
skills to a `track="skill"` `RecallFile` generated inside the workspace memorize workflow.
Living with both has surfaced a consistent coupling problem.

1. **One pipeline does everything, per file.** `memorize_workspace(folder)` is a fan-out:
   for each changed file it runs the full `memorize` workflow *plus* a `generate_skills`
   step, then rebuilds the entire `INDEX.md`/`MEMORY.md`/`SKILL.md` tree. Memory
   extraction, skill synthesis, and indexing all fire for every file regardless of what
   that file is for.

2. **`generate_skills` is a parallel mechanism that bypasses the entry plane.** It
   re-synthesizes skills from the raw preprocessed text (not from the extracted
   `RecallEntry`s), and persists them directly as `RecallFile(track="skill")`, bypassing
   the `RecallEntry → RecallFileEntry → RecallFile` cascade. That bypass *is* the cause of
   ADR 0006's own deferred open issue: skills have no provenance link, so they never
   invalidate on source change/delete.

3. **The `track` column exists only to jam two different things into one table.** Memory
   categories and skills share `RecallFile` and are split by `track`. That forced sharing
   is the root of the asymmetry and the `generate_skills` bypass.

4. **The read side is forked, not composed.** `retrieve_rag`/`retrieve_llm` (heavy
   intention-routing + sufficiency RAG over the structured store) and `retrieve_workspace`
   (flat embedding recall) share **no** handlers — `_rag_*`/`_llm_*` vs `_ws_*` are
   independent reimplementations of the same recall. The write side composes
   (`memorize_workspace` = `memorize` + one step); the read side does not.

The deeper observation: `INDEX` / `MEMORY` / `SKILL` are not three outputs of one process —
they are three different **treatments** of source material, with three different **read
models**. Routing them through one pipeline and one store is the coupling.

A second observation refines the design: **embedding search and a graph are separable.**
Embedding search (embed → vector rank) is a flat capability over a set of pages; a graph
adds edges + traversal. Of the three layers, memory and the workspace index are
*relational* (entities interlink; documents reference each other and have hierarchy —
traversal matters), while skills are a *retrieval* problem ("which skill fits my current
task" = flat top-k), where a graph adds cost for little value.

## Decision

Refactor `memorize`/`retrieve` into **three independent lines**, each fed by its own
source, owning its own store and output, and sharing a **layered wiki-graph kernel**.

### The three lines

| Line | Source | Output index | L0 → L1 → L2 (raw → doc → item slices) | Read |
| --- | --- | --- | --- | --- |
| **chat** | conversation logs | `MEMORY.md` | raw chat → memory category → paragraph slices | hybrid: embedding + BM25 |
| **workspace** | workspace files | `INDEX.md` | raw media → caption paragraph → caption slices | hybrid: embedding + BM25 |
| **skill** | execution / tool traces | `SKILL.md` | raw logs → skill md → per-skill descriptions | hybrid: embedding + BM25 |

Each line keeps the established output-file name as its L1 index/map, over its own L0/L1/L2 stores.

> **Note.** This section's original "graph wiki / graph traversal" framing is **superseded**
> by "Refinement: hybrid retrieval (embedding + BM25), no graph" below; there is no graph.

### Shared kernel (one implementation, three instances)

All three lines share one **in-process** kernel: record stores (resource / item / category),
embedding, **hybrid search (cosine embedding + BM25 keyword)**, rank, markdown render, and
manifest diff. There is **no graph layer** and no external database — see "Refinement: hybrid
retrieval" below.

### Per-line data model (independent stores, no `track`)

```
Node  (a wiki page / file):  id · slug · content(md) · embedding · source_ref · meta
Edge  (a [[wikilink]]):      from_node · to_node · type?      ← graph lines only
```

`INDEX.md` / `MEMORY.md` / `SKILL.md` are rendered deterministically from each line's Node
set. The three lines have **separate stores** — there is no shared table and no `track`
discriminator.

### Layer model: L0 / L1 / L2 (refines the data model above)

The generic "Node/Edge" sketch above is refined into three **representation layers**. **Every
line has all three.** The layers share a uniform *role* but hold line-specific artifacts, and
each is **derived from the one below** (L0 → L1 → L2):

| Layer | Role (uniform) | chat | workspace | skill |
| --- | --- | --- | --- | --- |
| **L0** | raw source (`resource`) | raw chat corpus | raw multimodal data | raw agent-run logs |
| **L1** | coarse document derived from L0 | the classified **memory category** file | the preprocessed **caption paragraph** | the **skill markdown** |
| **L2** (**item**) | fine slices/extracts of L1 — the **embed/search unit** | slices of the category's paragraphs | slices of the caption paragraph | the **description** extracted per skill |

- **L1 ⊇ L2 in every line**: an *item* (L2) is a slice/extract of its L1 document. This
  **inverts the earlier wording** ("L1 = atomic item, L2 = category"): now **L1 is the coarse
  document and L2 is the fine item**, consistently across all three lines.
- **Derivation** runs L0 → L1 → L2: preprocess the raw source into the L1 document, then
  slice/extract it into L2 items.
- Because the meanings are now per-line (and inverted from the old model), they **no longer map
  1:1 onto `Resource`/`RecallEntry`/`RecallFile`**; each line's store holds a resource (L0), a
  document (L1), and item slices (L2).

**Retrieval (hybrid, no graph, single pass).** The **L2 items are embedded**; a query runs
one hybrid pass — cosine embedding + BM25 keyword, each min-max normalized and fused — over
the L2 items, and the top items **roll up to their L1 document** (and its L0 resource) for the
result. No `item ↔ item` edges, no entity index, no traversal, no multi-hop.

**Markdown output.** `MEMORY.md` / `SKILL.md` render the **L1** documents (memory categories /
skills); `INDEX.md` indexes the **L0** resources. L2 items live only in the store as the
embed/search units, not as separate files.

**Seam with preprocessing.** Preprocessing is the **injected first step of every line's
memorize pipeline** (`preprocess → …`): it takes a source *reference* and produces the **L1
document** (e.g. caption paragraph / classified memory / skill md) from the raw L0 source;
slicing/extracting that document into **L2 items** is the next step. Like the other treatments
(embed, and the per-line slice/extract), `preprocess` is injected so lines stay testable; a
real implementation wraps `memu.preprocess` (fetch via blob + modality decode + describe).

> **Divergence note.** This redefinition inverts L1/L2 and gives every line all three layers,
> so it is **ahead of the current `memu.lines` code** (which still has L1 = atomic item, L2 =
> grouping, workspace with no L2, skill with no L1). The code will be re-aligned to this model.

### Refinement: hybrid retrieval (embedding + BM25), no graph

This **supersedes every "graph / edges / backlinks / traversal / entity linking / GraphRAG /
multi-hop" description earlier in this ADR.** L1 has **no connective structure**:

- **No graph.** No `item ↔ item` edges, no `neighbors` / `backlinks` / `traverse`.
- **No entity layer / GraphRAG / multi-hop.** No parallel entity store, no item→entity index,
  no entity-overlap ranking, no iterative expansion.

Retrieval is a **single pass, hybrid**: a cosine embedding score and a BM25 keyword score are
each min-max normalized across candidates and fused into one rank. No iteration, no graph
walk. All three lines retrieve this way, differing only in *what* they search and *what* they
return:

All three lines retrieve the same way — embed the **L2 items**, one hybrid pass, roll up to
the **L1 document**:

| Line | embeds / searches (L2 items) | rolls up to / returns (L1) |
| --- | --- | --- |
| **chat** | slices of the memory category's paragraphs | the memory category (file) |
| **workspace** | slices of the caption paragraph | the caption paragraph (and its L0 resource) |
| **skill** | descriptions extracted per skill | the skill markdown |

Rationale: without multi-hop traversal, an entity index is not a graph — it is only a ranking
feature, and it did not justify graph machinery here. Hybrid (embedding + keyword) is a
standard, cheap, single-pass retrieval covering both semantic and exact-term matches; a graph
/ entity / multi-hop signal can be added later as an explicit, measured enhancement if a
benchmark shows it helps.

Concretely, `Edge` / `neighbors` / `backlinks` / `traverse`, any entity store / item→entity
index, and any multi-hop loop are **not part of the design**. The stores hold records +
embeddings and expose a single `search(query_vec, query_text, k)` over the L2 items that fuses
cosine + BM25; the hits then roll up to their L1 document before returning.

### Per-line ingest treatment (the only code that differs)

Each line's ingest is `preprocess (raw L0 → L1 document)` → `slice/extract (L1 → L2 items)` → `embed`:

- **chat:** classify the conversation into a memory category (L1); slice its paragraphs into items (L2).
- **workspace:** preprocess media into a caption paragraph (L1); slice it into items (L2).
- **skill:** synthesize a skill markdown (L1) from the logs; extract a description per skill as the item (L2).

### Independent triggers

Each line has its own source manifest and change detection. A change under one line's
source rebuilds **only that line**; lines never trigger each other. (A change in `/chat`
no longer re-synthesizes skills or rebuilds the workspace index.)

### Shared, not duplicated

The kernel is one implementation; the three lines are instances of it. Existing low-level
utilities stay shared *calls*, not copies: `LocalFS` fetch, the preprocess registry
(modality handlers), the embedding clients / `ClientPool`, and the workflow engine. A
single **scope convention** (`user_id` / `where`) is preserved across all three lines so
cross-line scoping ("everything about user X") still works even though the stores are
separate.

## What this removes

- `RecallEntry` / `RecallFile` / `RecallFileEntry` and the `track` column → per-line
  `Node`/`Edge`.
- The monolithic per-file `memorize_workspace` pipeline and the `generate_skills` step →
  three ingest treatments.
- `retrieve_rag` / `retrieve_llm` / `retrieve_workspace` → one shared read mechanism
  (embedding search, plus graph traversal on the two graph lines).
- The skill provenance/deletion gap (ADR 0006 open issue): the skill line owns its store
  and bypasses nothing; deletion is driven by the line's own manifest.

## Consequences

Positive:

- Three high-cohesion modules replace the two ~1500-line `memorize.py`/`retrieve.py`
  mixins; each line is end-to-end self-contained (source → ingest → store → read →
  output).
- The `track` column and the `generate_skills` bypass are gone; the skill provenance gap
  is resolved structurally rather than deferred.
- The read side becomes coherent — one search mechanism (+ optional traversal) instead of
  three duplicated recall paths.
- Each line's structure matches its real need (graph for relational lines, flat for
  retrieval), instead of an over-imposed uniform shape.
- Independent triggers cut wasted work: a chat change no longer re-synthesizes skills or
  rebuilds the index.

Negative / costs:

- A large refactor with a data migration (track-based rows → per-line stores).
- **No cross-line edges:** an entity relevant to more than one line is duplicated, with no
  cross-domain traversal. Accepted as the separation tax; a read-only weak cross-line
  reference (e.g. a skill page citing a memory entity by URI) is a future option, not built
  now.
- The workspace graph relies on **structural** links to avoid LLM link-inference cost; richer
  semantic linking there is deliberately out of scope.
- Three stores instead of one: a cross-line query must hit three lines (mitigated by the
  shared scope convention).

## Open issues (deferred)

- **Skill source.** Assumed to be a `/log` (trace) folder. Whether skill is a primary
  source line or is *distilled* from the chat/workspace lines is unresolved; it changes
  whether skill is a true third line or a second-order derivation.
- **Migration mechanics** from the current `RecallFile(track=…)` schema to three per-line
  stores (sketch: `track=memory` → chat nodes; `track=skill` → skill nodes; resources/INDEX
  → workspace nodes).
- **Workspace linking** — keep it purely structural, or add light semantic linking later.

## Implementation plan

PoC the **workspace line first**: it has the least LLM (structural links, kept-whole pages)
and the clearest graph, so it best validates the Base + Graph kernel end-to-end before the
LLM-heavy chat and skill lines are built on the same kernel.

## Related ADRs

- Supersedes `docs/adr/0004-workspace-memorize-and-memory-file-system.md`
- Supersedes `docs/adr/0006-from-memory-item-category-to-tracked-workspace-memorization.md`
- Builds on `docs/adr/0001-workflow-pipeline-architecture.md` (the kernel still composes as
  workflow steps), `docs/adr/0002-pluggable-storage-and-vector-strategy.md`, and
  `docs/adr/0005-dedicated-embedding-package.md`.
