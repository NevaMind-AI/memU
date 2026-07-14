ADR 0009: Packaging the Codex Integration — pip, a CLI Seam, and One Config Loader

- Status: Accepted
- Date: 2026-07-13
- Builds on: ADR 0008 (two integration surfaces — hooks over a programmatic API), ADR 0007
  (three lines / per-project store)
- Scope: how the Codex integration is *installed and invoked* on a user's machine — the
  distribution, the retrieval invocation seam, and the runtime configuration. It does **not**
  revisit the engine or the source model settled in 0007/0008.

## Context

ADR 0008 defined *what* the Codex integration is: a host adapter binding two seams —
`on_turn` (record) and `on_prompt` (inject) — onto the same base-plane `memu` calls every
other surface uses. It deliberately left the *packaging* open.

Codex realizes those two seams concretely, and the realization forces three packaging
questions 0008 did not answer:

- **Record (`on_turn`)** is realized not as a per-turn hook but as a **scheduled "bridging"
  task** (see `src/memu/hosts/codex/BRIDGING_TASK.md`): a cron job that periodically walks new
  turns under `~/.codex/sessions`, runs a prepare → self-evolve → commit pipeline, and writes the
  results back to the store. Two of its three steps are **code** (`prepare`, `commit`) that
  `import memu` directly.
- **Inject (`on_prompt`)** is realized as a **UserPromptSubmit hook** that adds a single
  instruction telling the agent to retrieve memory relevant to the current query. The agent
  then issues a retrieval call itself.

That leaves three decisions the installer and the two seams must agree on:

1. **Distribution.** How is `memu` put on the user's machine — pip (Python) or npm (a JS
   reimplementation of the same surface)?
2. **Retrieval invocation.** When the inject hook fires, what does the agent actually run — a
   wrapped Python script, or a CLI command?
3. **Configuration.** `MemoryService` needs a non-trivial config (at minimum a database DSN
   and an embedding/LLM provider). Today the bridging scripts construct it with a placeholder
   (`MemoryService()  # fill in config if needed`). The recording seam (writes) and the
   injection seam (reads) **must** construct identical config or retrieval reads a different
   store than bridging wrote. How is that config decided at install time and shared?

The load-bearing constraint across all three: **record and inject share one store and one
embedding space** (ADR 0008's "one store, one semantics"). A query is embedded at inject time
and compared against vectors written at record time; if the DSN or the embedding
provider/model differ between the two seams, the comparison is meaningless and retrieval
silently returns nothing.

## Decision

### 1. Distribute via pip; do not ship a parallel npm package

memU is installed as a Python package (`pip install memu-py`), exposing two console entrypoints:
`memu` (the library's own surface) and `memu-codex` (the host adapter — see Decision 2). No npm
package is built for this integration.

Rationale — a Python runtime with `memu` importable is **not optional** on the Codex path: the
scheduled bridging task's prepare and commit steps `import memu` directly. Given Python is
mandatory for the record seam regardless, npm cannot *replace* it — it can only *add*
a second runtime and a second implementation of the retrieval surface, which must then be kept
byte-for-byte behavior-compatible with the Python one (the embedding gateway, `cosine_topk`
vector search, the repo layer, and the whole pydantic config surface that
`AgenticMixin.progressive_retrieve` touches). An npm package that merely shells out to the CLI
adds a dependency without removing the Python requirement. npm would be the right call only if
the goal were a *zero-Python* toolchain; the scheduled task makes that impossible here.

One runtime, one implementation, one thing to keep in sync.

### 2. Both seams are invoked through a CLI command, never a script path

Neither seam points the agent at a `python /abs/path/to/script.py` invocation. Both are `PATH`
commands on a host-adapter binary:

- inject → `memu-codex retrieve "<query>"`
- record → `memu-codex prepare` / `memu-codex commit` (embedded in the scheduled task's prompt)

There is no *semantic* difference between a command and a script — both end up calling the same
`MemoryService` method. The difference is entirely operational, and every operational axis
favors the command:

- **Reliable invocation.** After `pip install`, the binary is on `PATH` and the agent emits a
  stable string. A script forces the agent to reproduce an exact `<VENV_PYTHON> <ABS_PATH>` pair,
  and baking an absolute script path into a *cron prompt* — which is where the record seam lives —
  breaks the moment the directory moves or the venv is rebuilt. This was the original design and
  it was the most fragile thing about it.
- **One config path.** The CLI centralizes config construction (Decision 3). A standalone script
  re-implements it and invites drift — and drift here is not cosmetic, it silently breaks
  retrieval.
- **Stable contract.** `memu-codex retrieve <q>` is a versioned interface; a file path is not.

**Which retrieval.** The inject hook must *not* call `memu retrieve` — that is the LLM-routed
path (intention routing, sufficiency checks, summarization), far too heavy to run on every turn.
It calls `AgenticMixin.progressive_retrieve`: LLM-free, single-shot, embeds the query once and
ranks segments/files/resources.

> **Correction.** An earlier draft of this ADR justified a new subcommand by claiming
> "`retrieve-workspace` runs the heavy LLM-routed workflow." That is false. `retrieve_workspace`
> is *already* LLM-free and single-shot, and returns the same three layers as
> `progressive_retrieve`; the two differ only in that `progressive_retrieve` executes the stages
> inline rather than through the workflow engine. The heavy LLM-routed command is `retrieve`
> (no suffix). The decision to expose `progressive_retrieve` therefore rests on *where the verb
> lives* — on the host adapter, next to the hook that calls it — not on a capability
> `retrieve-workspace` lacks. Whether skipping the workflow engine buys enough to justify the
> separate code path is an open question (see below), not an established one.

**Which binary.** Retrieval is exposed on the *host adapter* (`memu-codex retrieve`), not on the
core `memu` CLI. The core binary stays the algorithm surface; host plumbing does not accrete onto
it. Because the inject seam is identical across hosts — the hook differs, the retrieval does not —
the implementation lives once in `memu.hosts.retrieval` and each host CLI registers it.

### 3. One config loader, sourced from a persisted env file — not per-script placeholders

Configuration is expressed as the **existing `MEMU_*` environment variables** (already defined
by the CLI: `MEMU_DB`, `MEMU_LLM_PROVIDER`, `MEMU_API_KEY`, …). We do **not** invent new config
keys. Two refinements make them safe for the Codex seams:

- **Persist to a file, not the interactive shell.** Install writes the collected values to a
  dotenv at a known absolute path (`~/.memu/config.env`). Scheduled tasks run with no reliable
  working directory and cannot be assumed to inherit an interactive shell's exported
  environment, so a file every entrypoint loads is the robust carrier; shell `export`s in a
  profile are not. Precedence is **process environment > file > default**, so a one-off override
  needs no file edit.
- **One shared loader is the single source of truth.** The service-construction logic that lived
  inside `cli.py` (`_build_service` / `_database_config`) is promoted to `memu.env`
  (`build_service_from_env()` / `database_config()`), and **every entrypoint calls it**: the
  `memu` CLI, `memu-codex retrieve`, and the bridging pipeline's prepare and commit. The
  `MemoryService()  # fill in config if needed` placeholders are gone.

We frame this as *single source of truth*, deliberately **not** as "best-effort loading."
Best-effort implies a silent fallback to defaults — which is precisely the failure mode to
avoid: an entrypoint that falls back to the default `./data/memu.sqlite3` while bridging wrote to
the configured DSN will "succeed" and retrieve nothing. Missing required config must surface, not
default: `build_service_from_env()` **raises** when `MEMU_DB` is unset rather than guessing.

Minimum an install must collect: `MEMU_DB` (the DSN) and the provider + API key. The provider
choice is load-bearing beyond credentials — it selects the **embedding** model, and record and
inject must embed in the same space (see Context); the shared loader guarantees they do.

## What this changes

- The Codex integration is a **pip install** of the existing package; no npm artifact is
  produced or maintained.
- A **second console script**, `memu-codex`, is added alongside `memu`. It carries both seams —
  `retrieve` (inject), and `prepare` / `commit` / `verify-resources` (record) — plus `doctor` and
  `docs`. The core `memu` CLI is **unchanged**: no new subcommand, no new flag.
- The `skills/codex-memu-task/` folder is **deleted**. Its scripts move into the package under
  `src/memu/hosts/`, split by what varies: `hosts/bridging/` is the host-agnostic pipeline
  (cursor, job templates, snapshot/diff, commit), `hosts/base.py` is the only host seam
  (`TranscriptSource`: where sessions live, how a record is shaped), and `hosts/codex/` is ~50
  lines of session parsing plus a thin CLI. A second host is a `TranscriptSource` and a CLI, not
  a forked pipeline.
- `cli.py`'s service-construction helpers are **extracted into `memu.env`**
  (`build_service_from_env` / `database_config`), used by the CLI *and* the bridging pipeline; the
  two `MemoryService()  # fill in config` placeholders are removed.
- Install grows a step that writes **`~/.memu/config.env`** with the chosen `MEMU_*` values;
  every entrypoint reads it, so record and inject provably agree on store and embedding space.
- Two agent-facing docs ship **inside the wheel** at `src/memu/hosts/codex/`: `INSTALL.md` (the
  three-part setup) and `BRIDGING_TASK.md` (the scheduled-task procedure), printable via
  `memu-codex docs`. Nothing else needs to be distributed — there is no skill folder for a user
  to copy and no script directory for a cron prompt to point at.

## Consequences

Positive:

- One runtime and one implementation of the retrieval surface — nothing to keep behavior-synced
  across languages.
- The inject hook and the scheduled task are guaranteed to hit the same store and embedding
  space, so retrieval actually finds what bridging wrote (the correctness invariant is
  structural, not a matter of the user setting two things consistently).
- Both seams are stable `PATH` commands. Nothing machine-specific is baked into a hook config or
  a cron prompt, so neither breaks when a directory moves or a venv is rebuilt.
- Config is decided once at install time and lives in one file read by every seam.
- The distributed footprint is *nothing*. The user installs a package; the guides ride along
  inside it. There is no folder to copy into a skills directory and no download step.
- The core `memu` CLI keeps describing the algorithm. Host plumbing lives on the host binary, so
  `memu --help` does not degrade into a grab-bag as hosts are added.

Negative / costs:

- Users without a usable Python environment cannot adopt the integration; there is no JS-only
  path (accepted — the scheduled task requires Python anyway).
- `~/.memu/config.env` stores an API key in plaintext on disk; its permissions and lifecycle
  are an install concern (see open issues).
- `build_service_from_env` couples the CLI and the bridging pipeline to one helper; a breaking
  change to it now touches every seam at once (the intended trade-off — that shared fate is
  exactly what keeps record and inject in agreement).
- A per-host binary means each new host re-exposes `retrieve`. Mitigated by implementing it once
  in `memu.hosts.retrieval` and having host CLIs *register* rather than redefine it, but the verb
  is still duplicated across `--help` outputs.
- The agent-facing guides are now versioned with the package: fixing a wording bug in `INSTALL.md`
  requires a release. Accepted — it is the same "versioned interface, no drift" trade the CLI
  decision makes, and it guarantees the guide matches the installed code.

## Open issues (deferred)

- **Secret handling.** Whether the API key belongs in `~/.memu/config.env` at all (vs. a
  keychain / OS secret store) is unspecified. Install currently sets `chmod 600`.
- **Concurrent hosts.** The session cursor is per-host
  (`.session_manifest.<host>.json`), but `~/.memu/jobs`, `~/.memu/sessions`, and the touched-file
  log are shared and wiped per run. Two hosts' bridging tasks running at the same time would race.
  Fine while Codex is the only host; must be settled before the second one ships.
- **Multi-project stores.** A single `~/.memu/config.env` assumes one store per machine; how
  per-project stores (ADR 0007) are selected at inject time on Codex is not addressed here.

## Related ADRs

- Builds on `docs/adr/0008-two-integration-surfaces-hooks-and-api.md` — this ADR is the
  concrete Codex packaging of its two seams: `on_turn` realized as the scheduled bridging task,
  `on_prompt` realized as the UserPromptSubmit inject hook, both over the same `memu` base
  plane.
- Builds on `docs/adr/0007-three-independent-memory-lines-wiki-graph.md` — the "one store, one
  embedding space" invariant this ADR's config decision protects is that ADR's per-project
  store.
