# Install memU for Claude Code

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

Installing memU on Claude Code is three parts:

1. **Install memU** — a Python package, and the store + provider it writes to.
2. **Register the bridging task** — the scheduled job that turns recent Claude
   Code sessions into durable memory (the *record* seam).
3. **Patch `~/.claude/CLAUDE.md`** — a standing instruction that tells you to pull
   relevant memory before you answer (the *inject* seam).

Parts 2 and 3 must share one store and one embedding space, or a query is
compared against vectors written elsewhere and retrieval silently returns
nothing. Part 1 is what makes them agree.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. A Python runtime is required
regardless, because the bridging task runs Python.

### 1.1 Install

```
pip install memu-cli
```

This puts `memu` (the library's own surface) and **`memu-claude-code`** (the
Claude Code adapter) on `PATH`. Both Part 2 (record) and Part 3 (inject) go
through `memu-claude-code`.

Confirm it resolves:

```
memu-claude-code --help
```

If it is not found, the install landed in an environment that isn't on your
`PATH`. Fix that now — the scheduled task in Part 2 runs from a bare,
non-interactive environment and needs this command to resolve there.

### 1.2 Configure the store and provider

memU needs a **database** and an **LLM/embedding provider**. Both seams read this
one config, so decide it once, here. Collect from the user (or reuse values they
already have — if another memU host adapter such as `memu-codex` is already set
up on this machine, `~/.memu/config.env` exists and **must be reused as is**;
skip to the verify gate):

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

Write them to **`~/.memu/config.env`**, which every memU command loads. Use an
**absolute** path for `MEMU_DB`, and `chmod 600` the file (the key is plaintext —
tell the user). Do **not** instead export these in a shell profile: the scheduled
task does not inherit your interactive shell.

### ✅ Verify Part 1

```
memu-claude-code doctor
```

It prints the store and provider it resolved and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** on a new store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that periodically mines recent sessions under
`~/.claude/projects` into durable memU memory, skills, and resources.

**Do not reinvent this.** Follow the packaged procedure:

```
memu-claude-code docs task
```

It is authoritative. In summary: you will settle a schedule with the user
(default: daily at midnight) and register a recurring headless Claude Code run —
via system cron (the default; launchd only if the user prefers it) invoking
`claude -p "<the prompt that document gives you verbatim>"` — that runs
`memu-claude-code prepare`, works through
`~/.memu/hosts/claude-code/jobs/*.txt` in order, then runs
`memu-claude-code commit`.

Nothing in that prompt is machine-specific. If you find yourself substituting an
absolute path into it, you are doing it wrong.

### ✅ Verify Part 2

Confirm the cron/launchd entry exists. Then dry-run the first step by hand:

```
memu-claude-code prepare
```

It should report how many sessions it prepared (zero, if there is nothing new
since the cursor — that is fine and correct).

---

## Part 3 — Patch `~/.claude/CLAUDE.md` with the retrieval instruction

The *inject* seam: a standing instruction in Claude Code's **global memory file**
telling you to pull relevant memory before you answer. Claude Code loads
`~/.claude/CLAUDE.md` into every session in every project, so the instruction is
simply always there — no hook, no wrapper, no per-turn process.

**Do not hand-write the instruction.** memU owns the text and installs it for you:

```
memu-claude-code install-instruction
```

It writes memU's block into `~/.claude/CLAUDE.md`, creating the file if it does
not exist, and prints the diff. It appends rather than overwrites (existing
content is backed up to `~/.claude/CLAUDE.md.bak`), and it is idempotent: the
text sits in a marked block that a re-run — or a later memU release — replaces in
place. `--dry-run` shows the diff without writing; `--print` prints just the
block.

### ✅ Verify Part 3

```
cat ~/.claude/CLAUDE.md
memu-claude-code retrieve "smoke test"
```

The memU block must appear exactly once, anything the user had there must be
intact, and `retrieve` must exit cleanly (empty result lists are fine). A *fresh*
Claude Code session is what picks up the new CLAUDE.md — do not be surprised that
the instruction is not in your own context yet.

---

## Done

Report back to the user: the store (`MEMU_DB`) and provider in use; the scheduled
job and its schedule in words; and that the retrieval instruction is now in
`~/.claude/CLAUDE.md`, taking effect in their next session. Record and inject
both read `~/.memu/config.env`, so they provably share one store — what the task
learns tonight is what retrieval finds tomorrow.
