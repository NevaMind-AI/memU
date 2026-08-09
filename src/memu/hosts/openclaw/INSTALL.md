# Install memU for OpenClaw

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.
>
> However this run ends — finished or abandoned — close it out with **Report
> the outcome to memU** at the bottom of this file.

Installing memU on OpenClaw is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent OpenClaw
   sessions into durable memory (the *record* seam).
3. **Patch `~/.openclaw/workspace/AGENTS.md`** — a standing instruction that
   tells the agent to pull relevant memory before answering (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

**Scope note.** This adapter reads every agent's transcripts under
`~/.openclaw/agents/`, in either shape OpenClaw has shipped: the current
per-agent SQLite store (`<agentId>/agent/openclaw-agent.sqlite`) and the legacy
JSONL files (`<agentId>/sessions/*.jsonl`). Both are read, so an install works
either side of the upgrade — and a session mined before it keeps its place in the
cursor after it. If this install runs a non-default state dir
(`OPENCLAW_STATE_DIR`), pass `--session-dir <state-dir>/agents` to `prepare`.

---

## Part 1 — Install memU

```
pip install --upgrade memu-cli
```

**`--upgrade` matters, and a bare install is not enough.** A machine that
already carries an older `memu-cli` keeps it otherwise, and this guide names
subcommands (`init`, `config`) that older builds answer with `invalid choice`.
If you meet that error anywhere below, you are on a stale build: upgrade, then
re-run the command that failed.

This puts `memu` and **`memu-openclaw`** on `PATH`. Confirm:
`memu-openclaw --help`. If it is not found, fix `PATH` now — the scheduled task
in Part 2 runs from a bare, non-interactive environment.

### 1.2 Configure the memory backend

**Never write `~/.memu/config.env` by hand.** No heredoc, no `echo >>`, no
editor. Every memU host on this machine shares that one file, it holds a
plaintext credential, and it carries an invariant a text edit cannot keep:
record and retrieval must agree on one backend — and in local mode on one store
and one embedding space — or retrieval keeps succeeding and finds nothing.
`memu-openclaw config` is the writer: it merges (anything it is not
given is left alone, including comments and another host's settings), sets
the file's permissions, and refuses the edits that break retrieval silently.

**Came from memU's `SKILL.md`? You already ran `init`** — it created the file
and, if the user handed over a memU Cloud key, already selected cloud memory.
Read the state below rather than assuming which.

If you came straight to this guide instead, run it now:

```
memu-openclaw init --cloud-api-key <the user's memU key>
```

Bare `memu-openclaw init` if the user has no key, or would rather keep memory
on this device. Re-running is harmless either way — `init` is idempotent and
keeps a mode it already finds. One caveat: passing a key selects **cloud**, and
on a machine already using local memory that is a switch. Nothing is deleted,
but memories written locally stop being retrieved; `init` warns and proceeds —
so if you are unsure what this machine already uses, read the state first and
say what the switch costs before you pass a key.

Reading the state writes nothing:

```
memu-openclaw config show
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
memu-openclaw config --cloud --cloud-api-key <memu-api-key>
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
memu-openclaw config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
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
memu-openclaw config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-base-url http://localhost:11434/v1 --embed-model nomic-embed-text --embed-api-key local
```

**Shell proxies: nothing to ask.** If `doctor` fails with a **502** against a
local embedding server, a proxy is hijacking localhost traffic. The proxy may
come from the shell's `HTTP_PROXY` — or from the OS's system-wide settings
(macOS: System Settings → Network → Proxies — a VPN
client typically turns this on), which `env | grep -i proxy`
will not show. Current memU bypasses proxies for loopback URLs automatically; on an
older release, set `NO_PROXY=localhost,127.0.0.1` for the commands that call
memU. A local server reached through a **non-loopback** address
(`host.docker.internal`, a LAN IP, a WSL or VM host address) needs the
`NO_PROXY` exemption on every release, with that address in the list. This is
a mechanical requirement with exactly one right answer — apply it and move on;
do not ask the user.

**The existing config fails doctor? Repair the connection, never the identity.**
If `~/.memu/config.env` predates this install and `doctor` fails, diagnose the
transport first — is the embedding server running, is a proxy in the way — before
changing anything. A connection-level repair is an ordinary `config` call and is
allowed to land:

```
memu-openclaw config --local --embed-base-url http://127.0.0.1:11434/v1
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
memu-openclaw doctor
```

It prints the resolved mode plus its endpoint or local store/provider and must
exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
backend.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that mines recent transcripts under
`~/.openclaw/agents/*/sessions/` into memU memory, skills, and resources. In
cloud mode, workspace resources are submitted but are not currently persisted.
**Do not reinvent this** — follow the packaged procedure:

```
memu-openclaw docs task
```

In summary: settle a schedule with the user (default: every hour) and
create an **OpenClaw cron job** — OpenClaw schedules agent runs natively — whose
recurring prompt is the block that document gives you verbatim: it runs
`memu-openclaw prepare`, works through `~/.memu/hosts/openclaw/jobs/*.txt` in
order, then `memu-openclaw commit`. Nothing in it is machine-specific.

### ✅ Verify Part 2

Confirm the cron job exists with the expected schedule, then dry-run:
`memu-openclaw prepare` (zero prepared sessions is fine and correct when nothing
is new).

---

## Part 3 — Install the retrieval skill and point the workspace `AGENTS.md` at it

The *inject* seam: a standing instruction in OpenClaw's **workspace AGENTS.md**
telling the agent to pull relevant memory before answering. OpenClaw loads
`~/.openclaw/workspace/AGENTS.md` at the start of every session, so the
instruction is simply always there.

**Do not hand-write the instruction.** memU owns the text and installs it:

```
memu-openclaw install-instruction
```

One command, two files, because OpenClaw has skills:

- `~/.openclaw/skills/memu-retrieve/SKILL.md` — the procedure: the `retrieve`
  command to run and how to read the layers that come back. `~/.openclaw/skills`
  is OpenClaw's managed skills directory; this subfolder is memU's own, so a
  re-run overwrites it whole.
- `~/.openclaw/workspace/AGENTS.md` — two sentences telling the agent to use that
  skill before answering. The detail stays out of here on purpose: AGENTS.md is
  in context on every turn, whether or not the turn touches memory; the skill is
  loaded only when the agent acts on it.

It creates either file if absent and prints the diff of both. `AGENTS.md` is the
*user's*, so it appends rather than overwrites (previous content is backed up to
`~/.openclaw/workspace/AGENTS.md.bak`), and memU's text sits in a marked block
that a re-run — or a later memU release — replaces in place. `--dry-run` shows
the diffs without writing; `--path` and `--skills-dir` target a non-default
workspace or skills directory. If this host uses a non-default state dir
(`OPENCLAW_STATE_DIR`), the managed skills root is `<state-dir>/skills` — pass
that as `--skills-dir` (and the workspace `AGENTS.md` as `--path` when the
workspace is not the default either).

### ✅ Verify Part 3

```
cat ~/.openclaw/workspace/AGENTS.md
cat ~/.openclaw/skills/memu-retrieve/SKILL.md
memu-openclaw retrieve "smoke test"
```

The memU block must appear exactly once and name the `memu-retrieve` skill, that
skill must exist, anything the user had in `AGENTS.md` must be intact, and
`retrieve` must exit cleanly (empty lists are fine). A fresh OpenClaw session is
what picks up the new AGENTS.md and skill.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-openclaw` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-openclaw report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-openclaw report error --stage install --detail "<a full account of what went wrong>"
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

Report back to the user: the selected mode and its cloud endpoint or local store/provider; the cron job's name and
schedule in words; and that the retrieval instruction is now in the workspace
AGENTS.md, pointing at the `memu-retrieve` skill and taking effect next session.
Record and inject both read `~/.memu/config.env`, so they provably share one
backend.
