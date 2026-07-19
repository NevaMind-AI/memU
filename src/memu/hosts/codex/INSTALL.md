# Install memU for Codex

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

Installing memU on Codex is three parts:

1. **Install memU** — a Python package, and the store + provider it writes to.
2. **Register the bridging task** — the scheduled job that turns recent Codex
   sessions into durable memory (the *record* seam).
3. **Patch `~/.codex/AGENTS.md`** — a standing instruction that tells you to pull
   relevant memory before you answer (the *inject* seam).

Parts 2 and 3 must share one store and one embedding space, or a query is
compared against vectors written elsewhere and retrieval silently returns
nothing. Part 1 is what makes them agree.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. There is no npm package — do not look
for one; a Python runtime is required regardless, because the bridging task runs
Python.

### 1.1 Install

```
pip install memu-cli
```

This puts two commands on `PATH`:

- **`memu`** — memU itself (commit, list-files, retrieve). The library's own
  surface; this guide does not use it directly.
- **`memu-codex`** — the Codex adapter. Both Part 2 (record) and Part 3 (inject)
  go through it.

Confirm it resolves:

```
memu-codex --help
```

If it is not found, the install landed in an environment that isn't on your
`PATH`. Fix that now rather than working around it — the scheduled task in Part 2
and the hook in Part 3 both need this command to resolve from a bare, non-
interactive environment.

### 1.2 Configure the store and provider

memU needs a **database** and an **LLM/embedding provider**. Both seams read this
one config, so decide it once, here.

Collect from the user (or reuse values they already have):

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

Write them to **`~/.memu/config.env`**, which every memU command loads:

```
MEMU_DB=/Users/<you>/.memu/memu.sqlite3
MEMU_EMBED_PROVIDER=openai
MEMU_API_KEY=<key or env-var name>
```

Use an **absolute** path for `MEMU_DB`. A relative one resolves against the
working directory, and the scheduled task has no reliable working directory.

> Do **not** instead export these in a shell profile. The scheduled task does not
> inherit your interactive shell. The file is the carrier; a profile export is
> not. (A `MEMU_*` variable that *is* set in the environment wins over the file,
> so you can still override for one command.)

The API key sits in plaintext in this file. Tell the user, and set the
permissions: `chmod 600 ~/.memu/config.env`.

### ✅ Verify Part 1

```
memu-codex doctor
```

It prints the store and provider it resolved and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** — the store is new; you
are testing that config resolves and the store answers, not that it has content.

If it errors, fix `~/.memu/config.env` before continuing. Both later parts depend
on this working, and both fail *silently* if it is wrong.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a Codex scheduled task that periodically mines recent
`~/.codex/sessions` into durable memU memory, skills, and resources.

**Do not reinvent this.** Follow the packaged procedure:

```
memu-codex docs task
```

It is authoritative. In summary, you will settle a cron schedule with the user
(default: every hour, `0 * * * *`) and create a Codex scheduled task whose
recurring prompt is the three-step block that document gives you verbatim —
`memu-codex prepare`, then the agent works through `~/.memu/jobs/*.txt` in order,
then `memu-codex commit`.

Nothing in that prompt is machine-specific. If you find yourself substituting an
absolute path into it, you are doing it wrong.

### ✅ Verify Part 2

Confirm the scheduled task exists with the expected name and cron. Then dry-run
the first step by hand:

```
memu-codex prepare
```

It should report how many sessions it prepared (zero, if there is nothing new
since the cursor — that is fine and correct). Report the task name and schedule
back to the user.

---

## Part 3 — Patch `~/.codex/AGENTS.md` with the retrieval instruction

The *inject* seam: a standing instruction in Codex's **global AGENTS.md** telling
you to pull relevant memory before you answer. Codex loads `~/.codex/AGENTS.md`
into every session, so the instruction is simply always there — no hook, no
wrapper, no per-turn process. You run the retrieval yourself and factor the
results into your answer.

**Do not hand-write the instruction.** memU owns the text and installs it for you:

```
memu-codex install-instruction
```

That is the whole step. It writes memU's block into `~/.codex/AGENTS.md`, creating
the file if it does not exist, and prints the diff of what it changed.

Three properties worth knowing, because they are what make it safe to just run:

- **It appends; it never overwrites.** `~/.codex/AGENTS.md` is the *user's* global
  instruction file and may already hold rules that have nothing to do with memU.
  Everything already in there survives, and the previous contents are backed up to
  `~/.codex/AGENTS.md.bak` before anything is written.
- **It is idempotent.** memU's text goes inside a marked block. Re-running replaces
  that block in place rather than appending a second copy, so running it twice is
  harmless — and so a later memU release can *improve* the instruction and have the
  upgrade actually reach users who already installed it. A copy pasted in by hand
  could never be upgraded.
- **It shows its work.** `--dry-run` prints the diff and writes nothing; `--print`
  prints just the block. If the user wants to see what lands in their file before it
  lands, that is how.

If you want to read the instruction itself, run `memu-codex install-instruction
--print`. In short: it tells you to run `memu-codex retrieve "<query>"` before
answering — the LLM-free single-shot retrieval, not the LLM-routed `memu retrieve`,
which would cost an LLM call on every turn — and it explains how to read the
`segments`/`files`/`resources` layers that come back.

### ✅ Verify Part 3

Read the file back:

```
cat ~/.codex/AGENTS.md
```

The memU block must appear exactly once, and anything the user had in there
beforehand must still be intact.

Then confirm the command the instruction names actually works against the Part 1
store:

```
memu-codex retrieve "smoke test"
```

Empty result lists are fine — you are testing that the read path works, not that
the store has content yet.

Finally, note that a *fresh* Codex session is what picks up the new AGENTS.md. The
session you are installing from already loaded the old one, so do not be surprised
that the instruction is not in your own context yet.

---

## Done

Report back to the user:

- the store (`MEMU_DB`) and provider now in use;
- the scheduled task's name and cron, in words (e.g. "hourly at :00 local");
- that the retrieval instruction is now in `~/.codex/AGENTS.md`, and that it takes
  effect in their next Codex session.

Record (Part 2) and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the store you configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
