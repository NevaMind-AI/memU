ADR 0006: From Memory Item/Category to a Tracked RecallFile/RecallEntry Store for Workspace Memorize/Retrieve

- Status: Accepted
- Date: 2026-06-30

## Context

ADR 0004 landed `memorize_workspace` and the markdown "memory file system", and
deliberately kept the `skill/` tree **synthesized at export time** from the shared
per-source description trunk (never persisted, never derived from extracted items).
Skills therefore live only on disk: `MemoryFilesBuilder.build` synthesizes a
`slug -> body` map via `MemorySynthesizer`, the exporter writes `skill/<slug>/SKILL.md`,
and an incremental update reads those files back off disk (`read_skills`) to feed the
"existing skills" half of the next synthesis.

This has grown awkward:

- skills are not first-class data — they cannot be scoped (`user_data`), queried, or
  reasoned about alongside the structured store; the markdown tree *is* the database;
- the "existing skills" context for incremental synthesis is recovered by parsing
  markdown back off disk, rather than read from a table;
- the memory track and the skill track are asymmetric: memory categories are
  `RecallFile` rows rendered deterministically into `memory/`, while skills are an
  ephemeral synthesis artifact with a parallel-but-different code path in the exporter.

Meanwhile the memory track already does, per source file in the `memorize_workspace`
loop, exactly the shape skills want: take preprocessed content, fold it into a durable
`RecallFile.summary` via an LLM patch. Skills should reuse that machinery.

This work lands on top of a domain-wide rename done as the first commit on the branch:
`MemoryItem` → `RecallEntry`, `MemoryCategory` → `RecallFile`, `CategoryItem` →
`RecallFileEntry` (and their repositories), a pure no-behavior-change rename that
establishes the `RecallFile`/`RecallEntry` vocabulary this ADR uses throughout.

## Decision

Make a **skill** a first-class `RecallFile`, distinguished from a memory category by a
new `track` column, and generate skills **inside the memorize workflow** (the
workspace path) rather than freshly at export time.

### Data model

- Add `RecallFile.track: str` with values `"memory" | "skill"`, defaulting to
  `"memory"`. Existing rows backfill to `"memory"`.
- Rename `RecallFile.summary` → `RecallFile.content`. The `summary` name predates the
  `MemoryCategory` → `RecallFile` rename; the column holds the file's body, so
  `content` is the correct name. (`RecallEntry.summary` is **unchanged** — only the
  file-level column is renamed.) Both changes ship in one migration since the `track`
  add already forces one.
- `get_or_create_category` keys on `(name, track, *scope)`, and the Postgres
  unique-with-scope index becomes `(name, track, *scope)`, so a skill and a memory
  category may share a name without colliding.

### Track isolation via `where`

Every `RecallFile` reader scopes by track through the existing `where` filter rather
than ad-hoc post-filtering:

- the memory/categorize/retrieve/CRUD paths and the exporter's `memory/` rendering
  read `track="memory"`;
- the skill generation step and (future) skill rendering read `track="skill"`.

This keeps skills out of memory retrieval/RAG scoring and out of `memory/`.

### Skill generation in the workflow

`_memorize_one` (the `memorize_workspace` per-file path) runs a **new** workflow
(`memorize_workspace`) — the existing `memorize` steps plus a skill-generation step —
rather than overloading the shared `memorize` pipeline (single-file `memorize()` is
unchanged, mirroring ADR 0004's "don't touch `memorize`" stance). The new step:

- runs per file, after the memory persist step, taking `preprocessed_resources` as
  input (it has no data dependency on the memory categorize/persist outputs);
- reads existing `track="skill"` `RecallFile`s as the "existing skills" context — read
  from the DB, not from disk — so file *N* sees skills created by files *1..N-1*;
- reuses the existing skill-synthesis prompt/algorithm (processed content + existing
  skills → skills to add/replace), now emitting `(name, description, body)`;
- persists each skill **directly** as a `RecallFile(track="skill", content=body)`,
  embedding `name + description`, bypassing the `RecallEntry` plane entirely;
- is gated behind `memory_files_config.synthesize`.

### Export (mirrors the memory track)

The exporter mirrors the memory track exactly: it renders each `track="skill"`
`RecallFile` deterministically into `skill/<slug>.md` (just as `memory/<slug>.md` is
rendered from memory-track files — one shared, track-agnostic renderer), and the
synthesizer's skill role is reduced to producing a single overview `SKILL.md` body (the
mirror of `MEMORY.md`) synthesized from the skill files' bodies, rather than the
per-skill bodies. The old description-based skill synthesis, the `RecallEntry` skill
bypass, and the `skill/<slug>/SKILL.md` folder layout are gone; `read_skills` is
replaced by `read_skill_body` (the SKILL.md-overview analog of `read_memory_body`).
`SKILL.md` falls back to a deterministic link index when `synthesize=False`, mirroring
`MEMORY.md`.

### Retrieve (consuming the track)

The `track` column also opens the read side. A new `retrieve_workspace` entry point — the
read-side analog of `memorize_workspace`, and the simple counterpart to the routing-heavy
`retrieve` — does single-shot, LLM-free retrieval: it embeds the query once and ranks the
file/entry/resource layers by vector similarity, with none of the intention routing,
sufficiency checks, or summarization of the RAG path. The file layer scopes by `track`
through `RetrieveFileConfig.tracks`, so skill-track `RecallFile`s can be retrieved (or
excluded) independently of the memory track — the read-side mirror of the track isolation
above. Driven by a new `RetrieveWorkspaceConfig`.

## Scope of these commits

This ADR spans four commits on the branch (a fifth — gating new-category creation behind
`allow_new_categories` — is an unrelated fix to the existing taxonomy path):

1. **Domain rename** (foundation). `MemoryItem` → `RecallEntry`, `MemoryCategory` →
   `RecallFile`, `CategoryItem` → `RecallFileEntry`, and the matching repositories. Pure
   rename, no behavior change; establishes the vocabulary the rest of this work assumes.
2. **Skill track + workflow.** Schema foundation (`track` column, `summary` → `content`,
   `(name, track)` keying, migration), track isolation (memory-track readers filter
   `track="memory"`), and the new `memorize_workspace` workflow with its per-file skill
   generation step that persists `track="skill"` `RecallFile`s.
3. **Export mirror.** `skill/<slug>.md` rendered deterministically from the DB + a
   synthesized/indexed `SKILL.md` overview, symmetric with `memory/` + `MEMORY.md`.
4. **Workspace retrieve.** The LLM-free `retrieve_workspace` path that reads the track
   back out — see "Retrieve (consuming the track)" above.

## Open issues (deferred)

- **Skill staleness / provenance on deletion.** By bypassing the `RecallEntry` plane,
  skill `RecallFile`s have no link back to the resources that produced them. The memory
  track invalidates correctly on file change/delete via
  `RecallEntry.resource_id → RecallFileEntry → category` cascade
  (`_cascade_delete_by_urls`); skills have no equivalent, so a skill derived from a
  now-deleted source file lingers. We do not yet have a chosen solution (candidates: a
  provenance link from skill files to contributing resources, or a full skill-track
  rebuild on `diff.has_removals`). Until then the skill track is **append/merge-only**
  and does not shrink on deletion. *A solution is expected in a future commit.*

- **Cost / latency.** Skill synthesis moves from ~1 merged LLM call per workspace sync
  to one call per added/modified file (consistent with how per-file memory summaries
  already work, and gated behind `synthesize`). Plus one `SKILL.md`-overview synthesis
  per export, the mirror of the existing `MEMORY.md` synthesis. Acceptable, but noted.

## Consequences

Positive:

- skills are first-class, scoped, queryable rows; the markdown tree stops being the
  only home for skills;
- the "existing skills" context for incremental generation is a table read, not a
  markdown re-parse;
- memory and skill tracks become symmetric (`RecallFile` rows distinguished by
  `track`), collapsing two divergent code paths;
- single-file `memorize()` stays untouched; the skill step lives only on the workspace
  path;
- making skills first-class rows lets the new `retrieve_workspace` path read them back by
  `track`, so the workspace gets a symmetric memorize/retrieve pair without skills needing
  a bespoke read path.

Negative:

- a schema migration is required (`track` add + `summary`→`content` rename); existing
  Postgres/SQLite deployments need it applied (fresh DBs get it from `create_all`);
- every `RecallFile` reader must now be track-aware, a cross-cutting concern threaded
  through `where`;
- deletion/provenance for skills is a known, deferred gap (see open issues).
