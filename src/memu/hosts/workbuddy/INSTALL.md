# Install memU for WorkBuddy

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

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
pip install --upgrade memu-cli
```

**`--upgrade` matters, and a bare install is not enough.** A machine that
already carries an older `memu-cli` keeps it otherwise, and this guide names
subcommands (`init`, `config`) that older builds answer with `invalid choice`.
If you meet that error anywhere below, you are on a stale build: upgrade, then
re-run the command that failed.

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

**Never write `~/.memu/config.env` by hand.** No heredoc, no `echo >>`, no
editor. Every memU host on this machine shares that one file, it holds a
plaintext credential, and it carries an invariant a text edit cannot keep:
record and retrieval must agree on one backend — and in local mode on one store
and one embedding space — or retrieval keeps succeeding and finds nothing.
`memu-workbuddy config` is the writer: it merges (anything it is not
given is left alone, including comments and another host's settings), sets
the file's permissions, and refuses the edits that break retrieval silently.

**Came from memU's `SKILL.md`? You already ran `init`** — it created the file
and, if the user handed over a memU Cloud key, already selected cloud memory.
Read the state below rather than assuming which.

If you came straight to this guide instead, run it now:

```
memu-workbuddy init --cloud-api-key <the user's memU key>
```

Bare `memu-workbuddy init` if the user has no key, or would rather keep memory
on this device. Re-running is harmless either way — `init` is idempotent and
keeps a mode it already finds. One caveat: passing a key selects **cloud**, and
on a machine already using local memory that is a switch. Nothing is deleted,
but memories written locally stop being retrieved; `init` warns and proceeds —
so if you are unsure what this machine already uses, read the state first and
say what the switch costs before you pass a key.

Reading the state writes nothing:

```
memu-workbuddy config show
```

If it reports a mode with a backend behind it, another memU host got here first:
**reuse it as is** and go to the verify gate. A file that declares no mode is
local mode, for backward compatibility with files written before the mode
existed — `config show` says so.

Otherwise ask the user to choose once:

- **MemU Cloud** — memory and embeddings are hosted; requires a memU API key.
- **This device** — a database and an embedding provider on this machine.

**MemU Cloud.** Ask the user for their memU API key. If they do not have one,
direct them to [memu.so](https://memu.so) to register and create one, then wait
for the key before continuing.

```
memu-workbuddy config --cloud --cloud-api-key <memu-api-key>
```

It reports where the file is and what protection it has; tell the user the key
is stored there in plaintext. The production endpoint defaults to
`https://api.memu.so/api/v4/memory/` — pass `--cloud-base-url` only for a
non-default one, and never `--embed-api-key`, which is the *embedding
provider's* credential and has no role in cloud mode.

Cloud currently persists memory and skill recall files. It accepts workspace
resources from the existing bridging pipeline for compatibility but does not
persist or retrieve them yet; tell the user. Then skip the local-mode guidance
below and go to the verify gate.

**This device.** "This device" describes memory storage; it is fully offline
only when the embedding provider is local too. One command carries the lot:

```
memu-workbuddy config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
```

| Setting | Flag | Example |
| --- | --- | --- |
| Database | `--db` | an absolute path (`~/.memu/memu.sqlite3`), or a `postgres://…` DSN |
| Embedding provider | `--embed-provider` | `openai`, `jina`, `voyage`, … |
| Embedding model | `--embed-model` | the provider's default if omitted |
| Embedding credential | `--embed-api-key` | the provider's key — **not** the memU one |
| Embedding endpoint | `--embed-base-url` | a local OpenAI-compatible server |

Only the flags you pass are written, so a later run can add one without
disturbing the rest. Give `--db` an **absolute** path: a relative one resolves
against a working directory the scheduled task does not have. And do not export
any of this in a shell profile instead — the scheduled task does not inherit
your interactive shell, so the file is the carrier.

**No embedding key? Say so, then use a local embedding server.** If the user has
no API key to give, tell them up front what that means: memory cannot be called
across devices — everything stays on this machine, in a local database created
for them (SQLite). Then configure exactly that — keep `openai` as the provider,
point the endpoint at a local OpenAI-compatible server (e.g. Ollama), and pass
any placeholder credential, which such a server ignores:

```
memu-workbuddy config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-base-url http://localhost:11434/v1 --embed-model nomic-embed-text --embed-api-key local
```

**The existing config fails doctor? Repair the connection, never the identity.**
If `~/.memu/config.env` predates this install and `doctor` fails, diagnose the
transport first — is the embedding server running, is a proxy in the way — before
changing anything. A connection-level repair is an ordinary `config` call and is
allowed to land:

```
memu-workbuddy config --local --embed-base-url http://127.0.0.1:11434/v1
```

The identity is the other matter. `--db`, `--embed-provider` and `--embed-model`
bind the embedding space every existing vector was written against, so `config`
**refuses to change one that is already set**: "fixing" it would strand the
user's whole store while retrieval went on succeeding and finding nothing. The
refusal names `--force`, which is for a store genuinely being replaced and never
for making `doctor` go green. If one of the three looks wrong, stop and ask the
user.

### ✅ Verify Part 1

```
memu-workbuddy doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** on a new store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that periodically mines recent WorkBuddy
sessions into memU memory, skills, and resources. In cloud mode, workspace
resources are submitted but are not currently persisted.

**Refresh an existing bridging registration before continuing.** Inspect
WorkBuddy's automation list. Match the current marker `{{task_name}}`, every
former name in {{former_task_names}}, or the complete memU bridging pipeline
prompt. Record its current RRULE and remove **only that confirmed automation**
through WorkBuddy's automation management. Re-list automations
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
