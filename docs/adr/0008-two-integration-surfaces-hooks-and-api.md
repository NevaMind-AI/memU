ADR 0008: Trajectory as the Source — Zero-Code Hooks over a Programmatic API

- Status: Proposed
- Date: 2026-07-07
- Builds on: ADR 0007 (three independent memory lines on a layered kernel), ADR 0001 (workflow pipelines)
- Refines: ADR 0007's source model (resolves its "skill source" open issue) and output model
  (no rendered index files: per-line folders of L1 documents, searched via a pure per-line
  embedding index of L2 items carrying L1-pointing metadata)

## Context

ADR 0007 settled the *engine*: three independent lines (chat / workspace / skill) over a
shared layered kernel, driven by `memorize-workspace` (write) and `retrieve-workspace`
(read), against a per-project store. What it did **not** settle is how an *agent* — Claude
Code, Codex, OpenClaw, Hermes, or an in-house one — actually feeds sources in and gets
memory back out during a live session.

Today there is effectively one path: a human (or an agent following `SKILL.md`) runs the
CLI by hand against a **curated folder** — sources are whatever someone placed under `chat/`
or `agent/`, and the directory decides the treatment. That is fine for "sync this folder,"
but it does not give an agent **continuous** memory: the user turns and the agent's own tool
trajectory are never captured unless someone remembers to save them, and retrieved memory is
never injected unless the agent explicitly asks.

The deeper problem is the **source model itself**. The richest record of a working session is
the agent's **trajectory** — the interleaved user messages, agent reasoning, and tool actions.
Asking users (or agents) to pre-sort that record into per-line source directories throws away
the fact that a single stretch of work simultaneously contains *who the user is*, *how the
agent got something done*, and *where the project stands*. The structural, directory-based
routing of ADR 0007's sources cannot see any of that.

Beyond the source model, two different consumers want two different things:

1. **A drop-in user** wants memory to "just work" with **no code changes** to their agent —
   install something, and the agent starts remembering across sessions.
2. **A builder** embedding memU inside their own agent wants **explicit control** — call
   retrieve at a chosen point, memorize a chosen artifact, with their own batching and
   scoping.

Trying to serve both with one mechanism has been the tension. A pure API serves the builder
but leaves the drop-in user writing glue. A pure "magic" integration serves the drop-in user
but is a black box the builder cannot steer. And every host agent exposes a **different** hook
system (Claude Code `settings.json` events, Codex/OpenClaw/Hermes each their own), so "just
use hooks" is not one integration but N.

## Decision

Three decisions: one philosophical (the source), one structural (the surfaces), one of
naming (the CLI).

### 1. Trajectory is the primary source; the three lines are three extractions from it

The agent's **trajectory** (user turns + agent actions/tool traces) becomes the primary raw
source. Instead of routing pre-sorted directories to lines, memorize runs a **semantic
extraction** over the trajectory that distills three kinds of memory — each landing on the
ADR 0007 line built for it. Concretely, each line's **L0 is a different projection of the
same trajectory** (see the layer mapping below), rather than a separate source folder.

The lines are **renamed after what they extract** — `memory` / `skill` / `project` are the
canonical terms from here on (ADR 0007's `chat` and `workspace` are the old names of the
`memory` and `project` lines respectively):

| Line (canonical term) | What it captures | ADR 0007 name / source dir | Output |
| --- | --- | --- | --- |
| **memory** | user facts, preferences, conversational context | chat (`/chat`) | `memory/` folder (L1 docs) + embedding index |
| **skill** | reusable procedures — how the agent accomplished something | skill (`/skill`) | `skill/` folder (L1 docs) + embedding index |
| **project** | the files the work touched — project state as reflected in their content | workspace (`/workspace`) | `project/` folder (L1 docs) + embedding index |

**Output model: per-line L1 folders + a pure per-line embedding index. No rendered index
files.** ADR 0007's single rendered files (`MEMORY.md` / `SKILL.md` / `INDEX.md`) are
**removed**, replaced by two artifacts per line:

- **Browsable output** — a folder per line (`memory/`, `skill/`, `project/`) holding **one
  markdown file per L1 document** (per memory category, per skill, per project document).
  The folder *is* the human-facing output; nothing is rendered on top of it.
- **Searchable output** — a **pure embedding index per line**: one embedding per **L2 item**,
  whose embedded content is the L2 slice itself and whose **metadata points to its L1
  document** (and through it, the L0 trajectory span). A retrieval hit rolls up L2 → L1 via
  that metadata alone; L2 items never materialize as files.

Rationale: a change to one document touches one file instead of rewriting a monolith; the
search path needs no rendered artifact at all — embeddings + metadata carry the full
L2 → L1 → L0 chain; and the on-disk names match the line terms exactly.

**Layer mapping.** Each line keeps ADR 0007's L0 → L1 → L2 derivation, but the L0s are now
three projections of the **same trajectory** instead of three separate source folders:

| Layer (role) | memory | skill | project |
| --- | --- | --- | --- |
| **L0** — the line's projection of the trajectory | the **user queries and agent responses only** (no tool/action traces) | the **entire user–agent trajectory** (turns + actions/tool traces) | the **contents of files** touched in the trajectory |
| **L1** — summarized document (one md file in the line's folder) | the summarized **memory file** | the synthesized **skill** | the **summary** of the file's content |
| **L2** — the embedded unit (metadata → L1) | **slices** of the memory file | the skill's **description** | **slices** of the summary |

Two properties distinguish this from ADR 0007's directory routing:

- **Extraction is one-to-many, not routing.** A single turn can yield a user fact *and* a
  reusable skill *and* a project-state update; each extractor takes what it needs from the
  same trajectory. Directory routing was one-to-one by construction and could never do this.
- **The intelligence moves from the caller into the pipeline.** Nobody pre-sorts sources; the
  classify/extract step (the L0 → L1 `preprocess` seam of each line, per ADR 0007) decides
  what a trajectory contains. Callers — human, hook, or code — just hand over raw trajectory.

This **resolves ADR 0007's open "skill source" question**: skill is *distilled from the
trajectory*, not a primary source line fed by a separate `/log` folder. It also shifts the
**project** line's meaning from "indexed multimodal files" (the old workspace framing) toward
**project memory**; direct file ingestion (pointing `memu memorize` at a curated folder)
remains supported as a secondary path on the same line.

### 2. Two integration surfaces, layered — not two parallel products

- **The API/CLI is the base plane.** `memu memorize` / `memu retrieve` (Decision 3; and the
  in-process service behind them) are the single source of truth. Everything writes to and
  reads from the same per-project store defined in ADR 0007.
- **Hooks are a zero-code wrapper built *on* that base plane.** The hook integration is not a
  second engine; it is an adapter layer that calls the same CLI/service on the agent's
  behalf. Because both surfaces share one store, a project can **mix** them freely — record
  via hooks, retrieve explicitly in code, or vice versa — with no divergence.

### Surface A — Hook integration (zero-code, default distribution)

An agent loads memU's `SKILL.md` for capability description, and a **host adapter** wires memU
into the agent's lifecycle. The adapter does exactly three things, and only these three:

1. **Load** — make `SKILL.md` (and the store location) visible to the agent as a capability.
2. **Record trajectory** — on each turn, append the user input and the agent's action/tool
   trace as raw trajectory, then trigger memorize. The adapter does **no sorting**: the
   pipeline's extraction step (Decision 1) distills memory / skill / project from it.
3. **Inject memory** — before the agent generates, retrieve against the current prompt and
   splice the results into the agent's context.

### The hook contract (one abstraction, N thin adapters)

Host hook systems are heterogeneous, so memU defines **one contract** with two seams, and each
host ships a **thin adapter** that maps its native events onto them:

| Seam | Fires | Does | memU call | Execution |
| --- | --- | --- | --- | --- |
| **`on_turn`** | after a turn completes (user msg + agent trace available) | append the turn's raw trajectory, trigger memorize (extraction distills memory/skill/project) | `memu memorize` | **async / background, non-blocking** |
| **`on_prompt`** | before the agent generates | retrieve for the current prompt, splice hits into context | `memu retrieve` | **synchronous, in the critical path** |

The adapter's whole job is to bind a host's native hook events to `on_turn` / `on_prompt`.
Concretely:

- **Claude Code** — `settings.json` hooks: a `Stop`/post-turn hook → `on_turn`; a
  `UserPromptSubmit` hook → `on_prompt`.
- **Codex / OpenClaw / Hermes** — each maps its own post-turn and pre-generation events onto
  the same two seams.

New hosts are added by writing one adapter, not by touching the kernel or the CLI.

### Execution model (per the decision above)

- **Recording is asynchronous.** `on_turn` enqueues; memorize runs in the background and must
  never block the conversation. It reuses ADR 0007's incremental manifest diff, so repeated
  turns are cheap and only changed sources are processed.
- **Injection is synchronous.** `on_prompt` does a single-shot `memu retrieve` (embedding +
  BM25 hybrid search, no LLM per ADR 0007) in the critical path, under a **token budget**, and
  **fails open**: a miss, a timeout, or an empty store injects nothing and the turn proceeds
  normally.

### Surface B — Programmatic API (code-level control)

Builders embedding memU call retrieve / memorize directly from their agent code (in-process
service or CLI/JSON), choosing their own timing, batching, and scope (`user_id` / `where`).
This is the base plane exposed directly — the same calls the hook adapters make, with no hook
layer in between.

### Shared invariants (hard constraints)

- **One store, one semantics.** Both surfaces target the same per-project store and the same
  three lines. Hook mode must not invent a private store or a divergent record format.
- **Scope convention preserved.** The ADR 0007 `user_id` / `where` scope convention holds
  across both surfaces, so cross-surface queries ("everything about user X") work regardless
  of how it was written.
- **Hooks add no engine.** Any behavior available via hooks must be expressible as base-plane
  calls; the adapter is orchestration only.

### 3. CLI: reclaim `memu memorize` / `memu retrieve` as the canonical pair

With the lines renamed (Decision 1), "workspace" no longer names a line — leaving the
`memorize-workspace` / `retrieve-workspace` commands carrying a retired term that now reads
as "one line" when they actually operate on the whole store. Rename the pair:

- **`memu memorize`** and **`memu retrieve`** become the **only** commands, carrying the new
  semantics (trajectory ingestion + extraction on the write side; hybrid search over all
  three lines on the read side).
- The **legacy single-file `memorize` / `retrieve`** (already deprecated, documented as
  never-fall-back) are **removed first**; the names are reclaimed only after removal, so no
  release ships two behaviors under one name.
- **`memorize-workspace` / `retrieve-workspace` are removed outright** — no alias, no
  deprecation window. This is a breaking major-update cut; adapters and `SKILL.md` ship the
  canonical names in the same release.

The accepted risk: both prior command generations break at once — old legacy users find the
reclaimed names doing something new, and `-workspace` users get command-not-found. Accepted
deliberately: this ADR is the major update, and a clean cut beats carrying a retired term in
an alias.

## What this changes

- **The terms unify around the extractions**: the three lines are canonically named
  **memory / skill / project** (renaming ADR 0007's `chat` and `workspace`); docs, CLI
  output, and code should converge on these three terms.
- **The output changes shape**: `MEMORY.md` / `SKILL.md` / `INDEX.md` are gone; each line
  yields a folder of L1 documents (`memory/` / `skill/` / `project/`, one file per document)
  plus a pure embedding index of L2 items whose metadata points back to L1.
- **The source model inverts**: from "users curate per-line source folders" to "the trajectory
  is the source; extraction curates." Directory-based routing (`chat/` → memory, `agent/` →
  skill) becomes a legacy/secondary ingestion path.
- The project line's center of gravity shifts from multimodal file indexing to **project
  memory**; ADR 0007's "skill source" open issue closes as *distilled from trajectory*.
- **The CLI collapses to one pair**: `memu memorize` / `memu retrieve` (new semantics); both
  the legacy single-file pair and `memorize-workspace` / `retrieve-workspace` are removed —
  no aliases.
- `SKILL.md` graduates from "instructions a human/agent follows to run the CLI" to "the
  capability surface a host adapter loads," while remaining valid for manual use.
- memU gains a small **host-adapter layer** (one thin adapter per host) as the unit of new
  integrations, with the two-seam contract as its only coupling to the engine.
- The API surface is stated as a **first-class, supported** integration path, not just an
  internal detail behind the CLI.

## Consequences

Positive:

- Drop-in users get continuous cross-session memory with no code changes; builders keep full
  programmatic control — from one engine, not two.
- Host heterogeneity is contained: adding Codex/OpenClaw/Hermes/etc. is one adapter against a
  fixed two-seam contract, not a bespoke integration each time.
- Async record + sync inject keeps the conversation responsive (no per-turn LLM blocking)
  while still injecting fresh memory before each generation.
- Mixing surfaces is safe by construction because both hit the same store with the same scope
  convention.

Negative / costs:

- **Extraction is not free.** Directory routing was structural (zero-cost); semantic
  extraction over trajectory is LLM work on every memorize, and a misclassifying extractor
  pollutes lines silently — quality now depends on prompts, not conventions.
- N host adapters to build and maintain; each host's hook system evolves independently and can
  break its adapter.
- Async recording means a just-finished turn may not yet be retrievable on the immediately
  following prompt (eventual, not read-your-writes, consistency) — accepted for
  responsiveness.
- Synchronous injection adds retrieve latency to every prompt; bounded by the token/time
  budget and fail-open behavior, but non-zero.
- Auto-recording every turn raises **privacy/scope** questions (what gets persisted, and under
  whose `user_id`) that manual CLI use did not.

## Open issues (deferred)

- **Injection shape & budget.** Where retrieved memory lands (system-prompt append vs. a
  dedicated context block), and the exact token budget / ranking cutoff, are unspecified here.
- **Record batching policy.** Per-turn vs. per-session flushing, and debounce/coalescing of
  rapid turns, are left to the adapter; a shared default is TBD.
- **Extraction quality bar.** What counts as a *skill-worthy* procedure or a *project-worthy*
  state change (vs. noise) is a prompt/heuristic question for the extraction step; the
  one-to-many contract is decided here, the classifier itself is not.
- **Trajectory format.** The wire format a host adapter emits (full transcript vs. structured
  turn events, tool-output truncation) is per-adapter for now; a shared schema is TBD.
- **Privacy controls.** Opt-out, redaction, and per-turn scoping of auto-recorded content are
  not designed yet.

## Related ADRs

- Builds on `docs/adr/0007-three-independent-memory-lines-wiki-graph.md` (engine, three lines,
  store, `memorize-workspace` / `retrieve-workspace`); **refines its source model** —
  trajectory replaces per-line source folders as the primary source, its "skill source"
  open issue is resolved as *distilled from trajectory*, its `chat` / `workspace` lines
  are renamed **memory** / **project**, and its rendered `MEMORY.md` / `SKILL.md` /
  `INDEX.md` outputs are replaced by per-line L1 folders plus a pure per-line embedding
  index of L2 items.
- Builds on `docs/adr/0001-workflow-pipeline-architecture.md` (both surfaces drive the same
  workflow pipelines).
