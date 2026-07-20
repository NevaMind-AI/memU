# Install memU for any agent (`memu-agent`)

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

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

## Part 1 — Configure the store and provider

If another memU host adapter is already set up on this machine,
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

**Shell proxies: nothing to ask.** If `doctor` fails with a **502** against a
local embedding server, the shell's `HTTP_PROXY` is hijacking localhost
traffic. Current memU bypasses proxies for loopback URLs automatically; on an
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

Must exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
store.

---

## Part 2 — Memorization (only if detect said it works)

Register the bridging task against the session directory detect found. Follow
the packaged procedure:

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

## Done

Report back to the user:

- **which seams work**: memorization (and from which session directory),
  retrieval (and into which instruction file), both, or neither;
- the store (`MEMU_DB`) and provider in use;
- what was scheduled and where the instruction landed, for the seams that work.

Both seams read `~/.memu/config.env`, so they provably share one store — and
they share it with every dedicated adapter too: what this agent's sessions
teach memU, every other integrated agent retrieves.
