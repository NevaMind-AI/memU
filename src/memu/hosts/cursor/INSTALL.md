# Install memU for Cursor

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

Installing memU on Cursor is three parts:

1. **Install memU** — a Python package, and the store + provider it writes to.
2. **Register the bridging task** — the scheduled job that turns recent Cursor
   agent sessions into durable memory (the *record* seam).
3. **Patch `AGENTS.md`** — a standing instruction that tells the agent to pull
   relevant memory before answering (the *inject* seam).

Parts 2 and 3 must share one store and one embedding space, or a query is
compared against vectors written elsewhere and retrieval silently returns
nothing. Part 1 is what makes them agree.

**Scope note.** This adapter reads the **Cursor Agent** transcripts under
`~/.cursor/projects/` — the CLI (`cursor-agent`) and background agents. The IDE's
Composer chat history lives inside the editor's own SQLite state (`state.vscdb`)
and is not mined.

---

## Part 1 — Install memU

```
pip install memu-cli
```

This puts `memu` and **`memu-cursor`** on `PATH`. Confirm: `memu-cursor --help`.
If it is not found, fix `PATH` now — the scheduled task in Part 2 runs from a
bare, non-interactive environment.

### 1.2 Configure the store and provider

memU needs a **database** and an **LLM/embedding provider**. Both seams read this
one config. If another memU host adapter is already set up on this machine,
`~/.memu/config.env` exists and **must be reused as is**; skip to the verify
gate. Otherwise collect from the user:

| Setting | Env var | Example |
| --- | --- | --- |
| Database | `MEMU_DB` | `~/.memu/memu.sqlite3`, or a `postgres://…` DSN |
| Embedding provider | `MEMU_EMBED_PROVIDER` | `openai`, `jina`, `voyage`, … |
| API key | `MEMU_API_KEY` | the key, or the name of an env var holding it |

**No `MEMU_API_KEY`? Say so, then go local.** If the user has no API key to
give, tell them up front what that means: memory cannot be called across
devices — everything stays on this machine, in a local database created for
them (SQLite, e.g. `~/.memu/memu.sqlite3`). Then configure exactly that: keep
`MEMU_EMBED_PROVIDER=openai`, point `MEMU_BASE_URL` at a local
OpenAI-compatible embedding server (e.g. Ollama at `http://localhost:11434/v1`
with `MEMU_EMBED_MODEL=nomic-embed-text`), and set `MEMU_API_KEY` to any
placeholder value — a local server ignores it.

Write them to **`~/.memu/config.env`** (absolute `MEMU_DB` path, `chmod 600`,
never a shell-profile export — the scheduled task does not inherit your shell).

### ✅ Verify Part 1

```
memu-cursor doctor
```

Must exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that mines recent transcripts under
`~/.cursor/projects/*/agent-transcripts/` into durable memU memory, skills, and
resources. **Do not reinvent this** — follow the packaged procedure:

```
memu-cursor docs task
```

In summary: settle a schedule with the user (default: daily at midnight) and
register a cron entry that runs `cursor-agent -p "<the prompt that document gives
you verbatim>"` — the prompt runs `memu-cursor prepare`, works through
`~/.memu/hosts/cursor/jobs/*.txt` in order, then `memu-cursor commit`. Nothing in
it is machine-specific.

### ✅ Verify Part 2

Confirm the cron entry exists, then dry-run: `memu-cursor prepare` (zero prepared
sessions is fine and correct when nothing is new).

---

## Part 3 — Patch `AGENTS.md` with the retrieval instruction

The *inject* seam. Cursor's Agent reads `AGENTS.md` from the **project root** —
there is no global user-level instruction file the CLI honors (the IDE's User
Rules live in editor settings, out of reach here). So the instruction is
installed **per project**:

```
cd <the project> && memu-cursor install-instruction
```

It writes memU's block into `./AGENTS.md`, creating the file if absent, and
prints the diff. It appends rather than overwrites (existing content is backed up
to `AGENTS.md.bak`), and it is idempotent: the text sits in a marked block that a
re-run — or a later memU release — replaces in place. `--dry-run` shows the diff
without writing; `--path` targets another file.

Repeat for each project that should retrieve from memU, and tell the user that a
new project needs this one command run once.

### ✅ Verify Part 3

```
cat AGENTS.md
memu-cursor retrieve "smoke test"
```

The memU block must appear exactly once, prior content intact, and `retrieve`
must exit cleanly (empty lists are fine). A fresh Cursor session picks up the new
AGENTS.md.

---

## Done

Report back to the user: the store and provider in use; the scheduled job and its
schedule in words; which projects got the `AGENTS.md` instruction. Record and
inject both read `~/.memu/config.env`, so they provably share one store.
