# Install memU for any agent (`memu-agent`)

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.
>
> However this run ends — finished or abandoned — close it out with **Report
> the outcome to memU** at the bottom of this file.

This is the **generic** adapter, for agents that do not have a dedicated memU
binary. It supports two seams, and — unlike the dedicated adapters — either may
turn out unavailable for a given agent:

- **Memorization (record):** works when the agent keeps a local session log
  whose records match a known JSONL dialect.
- **Retrieval (inject):** works when the agent loads an instruction file
  (`AGENTS.md`, `CLAUDE.md`, `SOUL.md`, a project-root `AGENTS.md`, …) that a
  standing retrieve instruction can be patched into.

Part 0 determines which of the two you get. **You must report the outcome to
the user** — "memorization works", "retrieval works", both, or neither — before
setting anything up.

---

## Part 0 — Detect what this agent supports

```
pip install --upgrade memu-cli
memu-agent detect
```

**`--upgrade` matters, and a bare install is not enough.** A machine that
already carries an older `memu-cli` keeps it otherwise, and this guide names
subcommands (`init`, `config`) that older builds answer with `invalid choice`.
If you meet that error anywhere below, you are on a stale build: upgrade, then
re-run the command that failed.

`detect` surveys `~` for agent installations (or probes one directory:
`memu-agent detect ~/.someagent`). For each it reports:

- **memorization: works** — it found session files and recognized their
  records; note the directory, Part 2 needs it. If it found sessions in a
  container it cannot read (SQLite), memorization is *not* available through
  this adapter — say so.
- **retrieval: works** — it found an instruction file; note the path, Part 3
  needs it. If none was found but the agent is known to read the project root's
  `AGENTS.md`, retrieval still works per project.
- **dedicated adapter** — the agent has its own binary (`memu-codex`,
  `memu-claude-code`, `memu-cursor`, `memu-openclaw`, `memu-hermes`). Stop and
  use that instead: `<binary> docs install`.

### ✅ Verify Part 0

Tell the user, in one or two sentences, exactly which seams work for their
agent and why (what was found, where). If **neither** seam works, stop here —
memU cannot integrate with this agent yet, and no amount of setup changes that.

---

## Part 1 — Configure the memory backend

**Never write `~/.memu/config.env` by hand.** No heredoc, no `echo >>`, no
editor. Every memU host on this machine shares that one file, it holds a
plaintext credential, and it carries an invariant a text edit cannot keep:
record and retrieval must agree on one backend — and in local mode on one store
and one embedding space — or retrieval keeps succeeding and finds nothing.
`memu-agent config` is the writer: it merges (anything it is not
given is left alone, including comments and another host's settings), sets
the file's permissions, and refuses the edits that break retrieval silently.

**Came from memU's `SKILL.md`? You already ran `init`** — it created the file
and, if the user handed over a memU Cloud key, already selected cloud memory.
Read the state below rather than assuming which.

If you came straight to this guide instead, run it now:

```
memu-agent init --cloud-api-key <the user's memU key>
```

Bare `memu-agent init` if the user has no key, or would rather keep memory on
this device. Re-running is harmless either way — `init` is idempotent and keeps
a mode it already finds. One caveat: passing a key selects **cloud**, and on a
machine already using local memory that is a switch. Nothing is deleted, but
memories written locally stop being retrieved; `init` warns and proceeds — so
if you are unsure what this machine already uses, read the state first and say
what the switch costs before you pass a key.

Reading the state writes nothing:

```
memu-agent config show
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
memu-agent config --cloud --cloud-api-key <memu-api-key>
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
memu-agent config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
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
memu-agent config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-base-url http://localhost:11434/v1 --embed-model nomic-embed-text --embed-api-key local
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
memu-agent config --local --embed-base-url http://127.0.0.1:11434/v1
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
memu-agent doctor
```

It prints the resolved mode plus its endpoint or local store/provider and must
exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
backend.

---

## Part 2 — Memorization (only if detect said it works)

Register the bridging task against the session directory detect found. Follow
the packaged procedure. In cloud mode, workspace resources are submitted by the
same pipeline but are not currently persisted:

```
memu-agent docs task
```

In summary: settle a schedule with the user (default: every hour) and
register a recurring run — the agent's own scheduler if it has one, system cron
otherwise — whose prompt runs
`memu-agent prepare --session-dir <detected dir>`, works through
`~/.memu/hosts/agent/jobs/*.txt` in order, then `memu-agent commit`.

> Integrating **several** generic agents on one machine? Give each its own
> working tree (`--base-dir ~/.memu/hosts/<name>` on `prepare` and `commit`) so
> their runs never share a jobs directory.

### ✅ Verify Part 2

```
memu-agent prepare --session-dir <detected dir>
```

It should report how many sessions it prepared (zero is fine and correct when
nothing is new).

---

## Part 3 — Retrieval (only if detect said it works)

Patch the instruction file detect found:

```
memu-agent install-instruction --path <detected file>
```

No global file, but the agent reads the project root's `AGENTS.md`? Run
`memu-agent install-instruction` inside each project instead.

It writes memU's block into the file, creating it if absent, and prints the
diff. It appends rather than overwrites (existing content is backed up to
`<file>.bak`), and it is idempotent: the text sits in a marked block that a
re-run — or a later memU release — replaces in place.

### ✅ Verify Part 3

```
cat <detected file>
memu-agent retrieve "smoke test"
```

The memU block must appear exactly once, prior content intact, and `retrieve`
must exit cleanly (empty lists are fine). A fresh session of the agent picks up
the new instruction file.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-agent` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-agent report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-agent report error --stage install --detail "<a full account of what went wrong>"
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

- **which seams work**: memorization (and from which session directory),
  retrieval (and into which instruction file), both, or neither;
- the selected mode and its cloud endpoint or local store/provider;
- what was scheduled and where the instruction landed, for the seams that work.

Both seams read `~/.memu/config.env`, so they provably share one backend — and
they share it with every dedicated adapter too: what this agent's sessions
teach memU, every other integrated agent retrieves.
