# Install memU for Codex

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.
>
> However this run ends — finished or abandoned — close it out with **Report
> the outcome to memU** at the bottom of this file.

Installing memU on Codex is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent Codex
   sessions into durable memory (the *record* seam).
3. **Patch `~/.codex/AGENTS.md`** — a standing instruction that tells you to pull
   relevant memory before you answer (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. There is no npm package — do not look
for one; a Python runtime is required regardless, because the bridging task runs
Python.

### 1.1 Install

```
pip install --upgrade memu-cli
```

**`--upgrade` matters, and a bare install is not enough.** A machine that
already carries an older `memu-cli` keeps it otherwise, and this guide names
subcommands (`init`, `config`) that older builds answer with `invalid choice`.
If you meet that error anywhere below, you are on a stale build: upgrade, then
re-run the command that failed.

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

### 1.2 Configure the memory backend

**Never write `~/.memu/config.env` by hand.** No heredoc, no `echo >>`, no
editor. Every memU host on this machine shares that one file, it holds a
plaintext credential, and it carries an invariant a text edit cannot keep:
record and retrieval must agree on one backend — and in local mode on one store
and one embedding space — or retrieval keeps succeeding and finds nothing.
`memu-codex config` is the writer: it merges (anything it is not
given is left alone, including comments and another host's settings), sets
the file's permissions, and refuses the edits that break retrieval silently.

**Came from memU's `SKILL.md`? You already ran `init`** — it created the file
and, if the user handed over a memU Cloud key, already selected cloud memory.
Read the state below rather than assuming which.

If you came straight to this guide instead, run it now:

```
memu-codex init --cloud-api-key <the user's memU key>
```

Bare `memu-codex init` if the user has no key, or would rather keep memory on
this device. Re-running is harmless either way — `init` is idempotent and keeps
a mode it already finds. One caveat: passing a key selects **cloud**, and on a
machine already using local memory that is a switch. Nothing is deleted, but
memories written locally stop being retrieved; `init` warns and proceeds — so
if you are unsure what this machine already uses, read the state first and say
what the switch costs before you pass a key.

Reading the state writes nothing:

```
memu-codex config show
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
memu-codex config --cloud --cloud-api-key <memu-api-key>
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
memu-codex config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
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
memu-codex config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-base-url http://localhost:11434/v1 --embed-model nomic-embed-text --embed-api-key local
```

**Going local behind Codex's network proxy: nothing to ask.** Codex routes
shell traffic through its proxy, which cannot reach *your* `localhost` — the
symptom is `doctor` failing with a 502 against a local embedding server. (The
same 502 can come from the user's own shell `HTTP_PROXY`, or from the OS's
system-wide proxy — macOS: System Settings → Network → Proxies, typically turned on by a VPN
client — which
`env | grep -i proxy` will not show.)
Current memU bypasses proxies for loopback URLs automatically; if you see that
502 on an older release, set `NO_PROXY=localhost,127.0.0.1` for the commands
that call memU. The automatic bypass covers **loopback URLs only** — a local
server reached through a non-loopback address (`host.docker.internal`, a LAN
IP, a WSL or VM host address) still needs the `NO_PROXY` exemption on every
release, with that address in the list. Either way this is a mechanical
requirement with exactly one right answer — apply it and move on; do not ask
the user.

**The existing config fails doctor? Repair the connection, never the identity.**
If `~/.memu/config.env` predates this install and `doctor` fails, diagnose the
transport first — is the embedding server running, is a proxy in the way — before
changing anything. A connection-level repair is an ordinary `config` call and is
allowed to land:

```
memu-codex config --local --embed-base-url http://127.0.0.1:11434/v1
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
memu-codex doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** — the store is new; you
are testing that config resolves and the store answers, not that it has content.

If it errors, fix it with another `memu-codex config` call — never by editing
`~/.memu/config.env` — before continuing. Both later parts depend
on this working, and both fail *silently* if it is wrong.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a Codex scheduled task that periodically mines recent
`~/.codex/sessions` into memU memory, skills, and resources. In cloud mode,
workspace resources are submitted but are not currently persisted.

**Do not reinvent this.** Follow the packaged procedure:

```
memu-codex docs task
```

It is authoritative. In summary, you will settle a cron schedule with the user
(default: every hour, `0 * * * *`) and create a Codex scheduled task whose
recurring prompt is the three-step block that document gives you verbatim —
`memu-codex prepare`, then the agent works through `~/.memu/hosts/codex/jobs/*.txt` in order,
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

That is the whole step. It writes two files and prints the diff of each, creating
either if it does not exist:

- **`~/.codex/skills/memu-retrieve/SKILL.md`** — the procedure: the command to run
  and how to read what comes back.
- **`~/.codex/AGENTS.md`** — two sentences telling you to use that skill before
  answering.

The split is the point. AGENTS.md is in your context on *every* turn, whether or
not the turn has anything to do with memory, so it carries only what you need in
order to decide to retrieve; the skill carries the detail and is loaded only once
you act on it.

Three properties worth knowing, because they are what make it safe to just run:

- **It appends; it never overwrites.** `~/.codex/AGENTS.md` is the *user's* global
  instruction file and may already hold rules that have nothing to do with memU.
  Everything already in there survives, and the previous contents are backed up to
  `~/.codex/AGENTS.md.bak` before anything is written. (The skill directory is
  memU's own — nothing of the user's lives there — so it is simply overwritten.)
- **It is idempotent.** memU's text goes inside a marked block. Re-running replaces
  that block in place rather than appending a second copy, so running it twice is
  harmless — and so a later memU release can *improve* the instruction and have the
  upgrade actually reach users who already installed it. A copy pasted in by hand
  could never be upgraded. The same holds for the skill.
- **It shows its work.** `--dry-run` prints the diffs and writes nothing; `--print`
  prints what would be installed. If the user wants to see what lands in their file
  before it lands, that is how.

If you want to read the text itself, run `memu-codex install-instruction --print`.
In short: the skill tells you to run `memu-codex retrieve "<query>"` before
answering — the LLM-free single-shot retrieval, not the LLM-routed `memu retrieve`,
which would cost an LLM call on every turn — and it explains how to read the
`segments`/`files`/`resources` layers that come back.

### ✅ Verify Part 3

Read both files back:

```
cat ~/.codex/AGENTS.md
cat ~/.codex/skills/memu-retrieve/SKILL.md
```

The memU block must appear in AGENTS.md exactly once and name the `memu-retrieve`
skill, that skill must exist, and anything the user had in AGENTS.md beforehand
must still be intact.

Then confirm the command the skill names actually works against the Part 1
store:

```
memu-codex retrieve "smoke test"
```

Empty result lists are fine — you are testing that the read path works, not that
the store has content yet.

Finally, note that a *fresh* Codex session is what picks up the new AGENTS.md and
the new skill. The session you are installing from already loaded the old one, so
do not be surprised that the instruction is not in your own context yet.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-codex` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-codex report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-codex report error --stage install --detail "<a full account of what went wrong>"
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

Report back to the user:

- the selected mode and its cloud endpoint or local store/provider;
- the scheduled task's name and cron, in words (e.g. "daily at 00:00 local");
- that the retrieval instruction is now in `~/.codex/AGENTS.md`, pointing at the
  `memu-retrieve` skill, and that it takes effect in their next Codex session.

Record (Part 2) and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the backend configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
