ADR 0009: Packaging the Codex Integration — pip, a CLI Seam, and One Config Loader

- Status: Proposed
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
  task** (see `skills/codex-memu-task/SKILL.md`): a cron job that periodically walks new turns
  under `~/.codex/sessions`, runs a prepare → self-evolve → commit pipeline, and writes the
  results back to the store. Two of its three steps are **Python scripts** (`prepare_jobs.py`,
  `commit_results.py`) that `import memu` directly.
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

memU is installed as a Python package (`pip install`), exposing its existing console
entrypoint `memu`. No npm package is built for this integration.

Rationale — a Python runtime with `memu` importable is **not optional** on the Codex path:
the scheduled bridging task's `prepare_jobs.py` / `commit_results.py` `import memu` and require
a `<VENV_PYTHON>` that can resolve it (`SKILL.md` already makes this a hard prerequisite). Given
Python is mandatory for the record seam regardless, npm cannot *replace* it — it can only *add*
a second runtime and a second implementation of the retrieval surface, which must then be kept
byte-for-byte behavior-compatible with the Python one (the embedding gateway, `cosine_topk`
vector search, the repo layer, and the whole pydantic config surface that
`AgenticMixin.progressive_retrieve` touches). An npm package that merely shells out to the CLI
adds a dependency without removing the Python requirement. npm would be the right call only if
the goal were a *zero-Python* toolchain; the scheduled task makes that impossible here.

One runtime, one implementation, one thing to keep in sync.

### 2. Retrieval is invoked through the CLI, not a bespoke script

The inject hook points the agent at a **CLI command** (`memu retrieve "<query>"`), not at a
`python /abs/path/to/retrieve.py` invocation. Because the current `retrieve-workspace`
subcommand runs the heavy LLM-routed workflow rather than the LLM-free single-shot the hook
wants, we **add a thin subcommand** that wraps `AgenticMixin.progressive_retrieve` and prints
its JSON — reusing the CLI's existing config plumbing (`_build_service`).

There is no *semantic* difference between the two options — both ultimately call
`MemoryService(...).progressive_retrieve()`. The difference is entirely operational, and every
operational axis favors the CLI:

- **Reliable invocation.** After `pip install`, `memu` is on `PATH`; the agent emits a stable
  `memu retrieve "<query>"`. A script forces the agent to reproduce the exact
  `<VENV_PYTHON> <ABS_PATH>` pair that `SKILL.md` already documents as fragile, and baking an
  absolute script path into a hook config breaks the moment the skill directory moves.
- **One config path.** The CLI already centralizes config construction (Decision 3). A
  standalone script re-implements it and invites drift — and drift here is not cosmetic, it
  silently breaks retrieval.
- **Stable contract.** `memu retrieve <q>` is a versioned interface; a file path is not.

The cost is ~15 lines of subcommand wrapping code that already exists — far less than a bespoke
script, and it inherits config for free.

### 3. One config loader, sourced from a persisted env file — not per-script placeholders

Configuration is expressed as the **existing `MEMU_*` environment variables** (already defined
by the CLI: `MEMU_DB`, `MEMU_LLM_PROVIDER`, `MEMU_API_KEY`, …). We do **not** invent new config
keys. Two refinements make them safe for the Codex seams:

- **Persist to a file, not the interactive shell.** Install writes the collected values to a
  dotenv at a known absolute path (`~/.memu/config.env`). Scheduled tasks run with "no reliable
  working directory" (`SKILL.md`) and cannot be assumed to inherit an interactive shell's
  exported environment, so a file every entrypoint loads is the robust carrier; shell `export`s
  in a profile are not.
- **One shared loader is the single source of truth.** The service-construction logic today
  living inside `cli.py` (`_build_service` / `_database_config`) is promoted to a shared helper
  (e.g. `build_service_from_env()`), and **all four entrypoints call it**: the retrieve
  subcommand, `prepare_jobs.py`, `commit_results.py`, and any future CLI command. The bridging
  scripts' `MemoryService()  # fill in config if needed` placeholders are replaced by this call.

We frame this as *single source of truth*, deliberately **not** as "best-effort loading."
Best-effort implies a silent fallback to defaults — which is precisely the failure mode to
avoid: a script that falls back to the default `./data/memu.sqlite3` while bridging wrote to the
configured DSN will "succeed" and retrieve nothing. Missing required config should surface, not
default.

Minimum an install must collect: `MEMU_DB` (the DSN) and the provider + API key. The provider
choice is load-bearing beyond credentials — it selects the **embedding** model, and record and
inject must embed in the same space (see Context); the shared loader guarantees they do.

## What this changes

- The Codex integration is a **pip install** of the existing package; no npm artifact is
  produced or maintained.
- The `memu` CLI gains **one subcommand** exposing `progressive_retrieve` (LLM-free single-shot)
  as the retrieval seam the inject hook targets; `retrieve-workspace` (the heavy workflow) is
  left as-is.
- `cli.py`'s service-construction helpers are **extracted into a shared `build_service_from_env`**
  used by the CLI *and* the bridging scripts; the two `MemoryService()  # fill in config`
  placeholders in `prepare_jobs.py` / `commit_results.py` are removed.
- Install grows a step that writes **`~/.memu/config.env`** with the chosen `MEMU_*` values;
  every entrypoint reads it, so record and inject provably agree on store and embedding space.
- Documentation adds an agent-facing **`INSTALL.md`** (verify/install memU → register the
  scheduled bridging task → install the UserPromptSubmit inject hook).

## Consequences

Positive:

- One runtime and one implementation of the retrieval surface — nothing to keep behavior-synced
  across languages.
- The inject hook and the scheduled task are guaranteed to hit the same store and embedding
  space, so retrieval actually finds what bridging wrote (the correctness invariant is
  structural, not a matter of the user setting two things consistently).
- The agent's retrieval invocation is a stable `PATH` command, resilient to the skill directory
  moving and easy for the agent to emit correctly.
- Config is decided once at install time and lives in one file read by every seam.

Negative / costs:

- Users without a usable Python environment cannot adopt the integration; there is no JS-only
  path (accepted — the scheduled task requires Python anyway).
- `~/.memu/config.env` stores an API key in plaintext on disk; its permissions and lifecycle
  are an install concern (see open issues).
- Extracting `build_service_from_env` couples `cli.py` and the bridging scripts to one helper;
  a breaking change to it now touches every seam at once (the intended trade-off — that shared
  fate is exactly what keeps record and inject in agreement).

## Open issues (deferred)

- **Secret handling.** Whether the API key belongs in `~/.memu/config.env` at all (vs. a
  keychain / OS secret store), and what file permissions install should set, is unspecified.
- **Config precedence.** How `~/.memu/config.env` composes with an already-exported `MEMU_*`
  environment (file-wins vs. env-wins) needs a stated rule in the shared loader.
- **Subcommand naming.** The exact name/flag for the `progressive_retrieve` seam
  (`retrieve --progressive` vs. a distinct subcommand) is left to implementation.
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
