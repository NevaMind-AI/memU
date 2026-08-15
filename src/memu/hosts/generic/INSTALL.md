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
pip install memu-cli
memu-agent detect
```

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

If another memU host adapter is already set up on this machine,
`~/.memu/config.env` exists and **must be reused as is**; skip to the verify
gate. An existing file without `MEMU_MEMORY_MODE` is local mode for backward
compatibility.

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

Write them to **`~/.memu/config.env`** (absolute `MEMU_DB` path, `chmod 600`,
never a shell-profile export — a scheduled task does not inherit your shell).

**The existing config fails doctor? Repair the connection, never the
identity.** If `~/.memu/config.env` predates this install and `doctor` fails,
diagnose the transport first — is the embedding server running, is a proxy in
the way — before touching the file. A minimal connection-level edit (say,
`localhost` → `127.0.0.1`) is acceptable: back the file up first, and tell the
user what changed and why. Never change `MEMU_DB`, `MEMU_EMBED_PROVIDER`, or
`MEMU_EMBED_MODEL` on an existing store — those three bind the embedding
space, and "fixing" them silently splits the user's memory (old vectors become
unreachable until everything is re-embedded). If one of them looks wrong, stop
and ask the user.

### ✅ Verify Part 1

```
memu-agent doctor
```

It prints the resolved mode plus its endpoint or local store/provider and must
exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
backend.

---

## Part 2 — Memorization (only if detect said it works)

Register the bridging task against the session directory detect found. In
cloud mode, workspace resources are submitted by the same pipeline but are not
currently persisted.

**Refresh an existing bridging registration before continuing.** If a native
job or cron entry for this generic adapter exists, record its current cadence and
remove **only that entry**. A cron entry invokes
`~/.memu/hosts/agent/bridge.sh` or an old inline pipeline prompt; rewrite it with
`crontab -l | grep -vE 'hosts/agent/bridge\.sh|memU bridging pipeline' | crontab -`,
and use `crontab -r` only when no lines remain. Remove a native job only when
its prompt runs `memu-agent prepare --session-dir …`, its jobs, then
`memu-agent commit`. Verify the crontab or native scheduler no longer lists a
memU bridging entry while unrelated entries remain. Leave the store, session
cursor, working tree, and retrieval instruction untouched. An absent entry is
the normal first-install case. Reuse the recorded cadence below unless the user
requested a change.

Follow the current packaged procedure:

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
