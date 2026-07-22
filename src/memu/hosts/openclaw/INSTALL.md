# Install memU for OpenClaw

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

Installing memU on OpenClaw is three parts:

1. **Install memU** — a Python package, and the store + provider it writes to.
2. **Register the bridging task** — the scheduled job that turns recent OpenClaw
   sessions into durable memory (the *record* seam).
3. **Patch `~/.openclaw/workspace/AGENTS.md`** — a standing instruction that
   tells the agent to pull relevant memory before answering (the *inject* seam).

Parts 2 and 3 must share one store and one embedding space, or a query is
compared against vectors written elsewhere and retrieval silently returns
nothing. Part 1 is what makes them agree.

**Scope note.** This adapter reads the JSONL transcripts under
`~/.openclaw/agents/<agentId>/sessions/` (all agents). If this install runs a
non-default state dir (`OPENCLAW_STATE_DIR`), pass
`--session-dir <state-dir>/agents` to `prepare`; if it keeps transcripts in the
newer SQLite session target, this adapter cannot read them.

---

## Part 1 — Install memU

```
pip install memu-cli
```

This puts `memu` and **`memu-openclaw`** on `PATH`. Confirm:
`memu-openclaw --help`. If it is not found, fix `PATH` now — the scheduled task
in Part 2 runs from a bare, non-interactive environment.

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
never a shell-profile export — the scheduled task does not inherit your shell).

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
memu-openclaw doctor
```

Must exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that mines recent transcripts under
`~/.openclaw/agents/*/sessions/` into durable memU memory, skills, and
resources. **Do not reinvent this** — follow the packaged procedure:

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

## Done

Report back to the user: the store and provider in use; the cron job's name and
schedule in words; and that the retrieval instruction is now in the workspace
AGENTS.md, pointing at the `memu-retrieve` skill and taking effect next session.
Record and inject both read `~/.memu/config.env`, so they provably share one
store.
