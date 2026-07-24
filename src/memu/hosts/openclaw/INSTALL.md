# Install memU for OpenClaw

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

Installing memU on OpenClaw is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent OpenClaw
   sessions into durable memory (the *record* seam).
3. **Patch `~/.openclaw/workspace/AGENTS.md`** — a standing instruction that
   tells the agent to pull relevant memory before answering (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

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

### 1.2 Configure the memory backend

If `~/.memu/config.env` already exists from another memU host, reuse it as is
and skip to the verify gate. An existing file without `MEMU_MEMORY_MODE` is
local mode for backward compatibility.

Otherwise ask the user to choose once:

- **MemU Cloud** — memory and embeddings are hosted; requires a memU project API key.
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

## Done

Report back to the user: the selected mode and its cloud endpoint or local store/provider; the cron job's name and
schedule in words; and that the retrieval instruction is now in the workspace
AGENTS.md, pointing at the `memu-retrieve` skill and taking effect next session.
Record and inject both read `~/.memu/config.env`, so they provably share one
backend.
