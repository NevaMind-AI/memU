# Install memU for WorkBuddy

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.
>
> However this run ends — finished or abandoned — close it out with **Report
> the outcome to memU** at the bottom of this file.

Installing memU on WorkBuddy is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent WorkBuddy
   sessions into durable memory (the *record* seam).
3. **Patch `~/.workbuddy/SOUL.md`** — a standing instruction that tells you to
   pull relevant memory before you answer (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. A Python runtime is required
regardless, because the bridging task runs Python.

### 1.1 Install

```
pip install memu-cli
```

This puts `memu` (the library's own surface) and **`memu-workbuddy`** (the
WorkBuddy adapter) on `PATH`. Both Part 2 (record) and Part 3 (inject) go
through `memu-workbuddy`.

Confirm it resolves:

```
memu-workbuddy --help
```

If it is not found, the install landed in an environment that isn't on your
`PATH`. Fix that now — the scheduled task in Part 2 runs from a bare,
non-interactive environment and needs this command to resolve there.

### 1.2 Configure the memory backend

If `~/.memu/config.env` already exists from another memU host, reuse it as is
and skip to the verify gate. An existing file without `MEMU_MEMORY_MODE` is
local mode for backward compatibility.

Otherwise ask the user to choose once:

- **MemU Cloud** — memory and embeddings are hosted; requires a memU API key.
- **This device** — use the existing local database and embedding configuration.

For **MemU Cloud**, ask the user to provide their memU API key. If they do not
have one, direct them to [memu.so](https://memu.so) to register and create one,
then wait for the key before continuing. Write:

```env
MEMU_MEMORY_MODE=cloud
MEMU_CLOUD_API_KEY=<memu-api-key>
```

The production endpoint defaults to `https://api.memu.so/api/v4/memory/`. The
key is plaintext in this file: tell the user
and set user-only permissions (`chmod 600 ~/.memu/config.env` on POSIX; restrict
the file to the current user on Windows). Do not reuse `MEMU_API_KEY`, which is
for local embedding providers.

Cloud currently persists memory and skill recall files. It accepts workspace
resources from the existing bridging pipeline for compatibility but does not
persist or retrieve them yet; tell the user. After writing cloud configuration,
skip the remaining local-mode guidance and go to the verify gate.

For **This device**, write `MEMU_MEMORY_MODE=local` and collect the settings
below. "This device" describes memory storage; it is fully offline only when
the embedding provider is local too:

| Setting | Env var | Example |
| --- | --- | --- |
| Database | `MEMU_DB` | `~/.memu/memu.sqlite3`, or a `postgres://…` DSN |
| Embedding provider | `MEMU_EMBED_PROVIDER` | `openai`, `jina`, `voyage`, … |
| API key | `MEMU_API_KEY` | the key, or the name of an env var holding it |

**No embedding `MEMU_API_KEY`? Say so, then use a local embedding server.** If the user has no API key to
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
memu-workbuddy doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** on a new store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that periodically mines recent sessions under
`~/.workbuddy/projects` into memU memory, skills, and resources. In cloud mode,
workspace resources are submitted but are not currently persisted.

**Refresh an existing bridging registration before continuing.** Inspect
WorkBuddy's automation list as in `UNINSTALL.md` Part 1. If an automation whose
name or prompt identifies the memU bridging pipeline exists, record its current
RRULE, remove **only that automation** through WorkBuddy's automation management,
and verify it no longer appears. Leave the store, session cursor, working tree,
and retrieval instruction untouched. An absent automation is the normal
first-install case. Reuse the recorded RRULE below unless the user requested a
change.

**Do not reinvent this.** Follow the packaged procedure:

```
memu-workbuddy docs task
```

It is authoritative. In summary: you will settle a schedule with the user
(default: every hour) and register a WorkBuddy automation that runs
`memu-workbuddy prepare`, works through
`~/.memu/hosts/workbuddy/jobs/*.txt` in order, then runs
`memu-workbuddy commit`.

Nothing in that prompt is machine-specific. If you find yourself substituting an
absolute path into it, you are doing it wrong.

### ✅ Verify Part 2

Confirm the automation exists in WorkBuddy's automation list. Then dry-run the
first step by hand:

```
memu-workbuddy prepare
```

It should report how many sessions it prepared (zero, if there is nothing new
since the cursor — that is fine and correct).

---

## Part 3 — Patch `~/.workbuddy/SOUL.md` with the retrieval instruction

The *inject* seam: a standing instruction in WorkBuddy's **global behavior file**
telling you to pull relevant memory before you answer. WorkBuddy loads
`~/.workbuddy/SOUL.md` into every session, so the instruction is simply always
there — no hook, no wrapper, no per-turn process. The behavior belongs here, not
in `MEMORY.md` alongside user facts and conversation summaries.

**Do not hand-write the instruction.** memU owns the text and installs it for you:

```
memu-workbuddy install-instruction
```

It writes memU's block into `~/.workbuddy/SOUL.md`, creating the file if it
does not exist, and prints the diff. It appends rather than overwrites (existing
content is backed up to `~/.workbuddy/SOUL.md.bak`), and it is idempotent: the
text sits in a marked block that a re-run — or a later memU release — replaces in
place. `--dry-run` shows the diff without writing; `--print` prints just the
block.

For an install made by an older memU release, the command also removes only
memU's marked block from the former `~/.workbuddy/MEMORY.md` target after the
new `SOUL.md` block is safely installed. User-authored memory stays byte-for-byte
intact, and the previous file contents are backed up to `MEMORY.md.bak`. This
migration runs only for the default target; an explicit `--path` never rewrites
files under the default WorkBuddy home.

### ✅ Verify Part 3

```
cat ~/.workbuddy/SOUL.md
cat ~/.workbuddy/MEMORY.md
memu-workbuddy retrieve "smoke test"
```

The memU block must appear exactly once in `SOUL.md` and not at all in the legacy
`MEMORY.md`; anything the user had in either file must be intact, and `retrieve`
must exit cleanly (empty result lists are fine). A *fresh* WorkBuddy session is
what picks up the new SOUL.md — do not be surprised that the instruction is not
in your own context yet.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-workbuddy` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-workbuddy report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-workbuddy report error --stage install --detail "<a full account of what went wrong>"
```

**Be generous with `--detail`.** It is the whole of what a memU engineer will
have to work out what is broken on this machine, and a one-line summary tells
them almost nothing. Write a paragraph or two of plain language: which gate you
were on, what you ran, what happened instead of what the guide predicted, what
you had already tried, and what you believe the cause is. Your reading of the
failure is the part nobody else can reconstruct — that is what belongs here.
Report once for the run, not once per retry.

**Detailed, not a transcript.** Do not paste the traceback or raw command
output: memU reports the exception type and its frames on its own, so repeating
them only crowds out your account. And keep out, always: an API key, token, or
any other credential; an absolute path (`/Users/…`, `C:\Users\…`); a database
DSN or an endpoint URL; the user's memory content, file contents, or transcript
text. Describe those in words instead — *"the local embedding server answers 502
through what looks like a system proxy"* says everything useful and names
nothing secret.

## Done

Report back to the user: the selected mode and its cloud endpoint or local store/provider; the scheduled
automation and its schedule in words; and that the retrieval instruction is now in
`~/.workbuddy/SOUL.md`, taking effect in their next session. Record and inject
both read `~/.memu/config.env`, so they provably share one backend — what the task
learns tonight is what retrieval finds tomorrow.
