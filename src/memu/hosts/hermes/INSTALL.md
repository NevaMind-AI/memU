# Install memU for Hermes Agent

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.
>
> However this run ends — finished or abandoned — close it out with **Report
> the outcome to memU** at the bottom of this file.

Installing memU on Hermes is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent Hermes
   sessions into durable memory (the *record* seam).
3. **Patch `~/.hermes/SOUL.md`** — a standing instruction that tells the agent to
   pull relevant memory before answering (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

**Scope note.** This adapter reads Hermes's SQLite session store —
`~/.hermes/state.db` (the `sessions` and `messages` tables), opened read-only so
it never contends with the gateway's writer. If this install runs a non-default
home (`HERMES_HOME`, or a profile), pass `--session-dir <home>/state.db` to
`prepare`. The manual snapshots under `~/.hermes/sessions/saved/` are not mined.

---

## Part 1 — Install memU

```
pip install memu-cli
```

This puts `memu` and **`memu-hermes`** on `PATH`. Confirm: `memu-hermes --help`.
If it is not found, fix `PATH` now — the scheduled task in Part 2 runs from a
bare, non-interactive environment.

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
memu-hermes doctor
```

It prints the resolved mode plus its endpoint or local store/provider and must
exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
backend.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that mines recent sessions out of
`~/.hermes/state.db` into memU memory, skills, and resources. In cloud mode,
workspace resources are submitted but are not currently persisted.

**Refresh an existing bridging registration before continuing.** If an
OS-scheduled memU bridging entry exists, record its current cadence and remove
**only that entry**. On Unix, identify it by
`~/.memu/hosts/hermes/bridge.sh` or an old inline pipeline prompt, then rewrite
cron with `crontab -l | grep -vE 'hosts/hermes/bridge\.sh|memU bridging pipeline' | crontab -`.
Remove its `PATH=` line only if nothing else needs it, use `crontab -r` only when
no lines remain, and delete only the memU launchd plist when launchd was chosen.
On Windows run `memu-hermes schedule uninstall`. Also list
`hermes cron list --all` and remove every exact-name legacy native job
`memu-bridging-hermes` with `hermes cron remove <job-id>`. Verify `crontab -l`
(and launchd, if used) has no memU bridging entry while unrelated entries remain,
`memu-hermes schedule status` reports not registered on Windows, and the Hermes
list has no legacy job. Leave the store, session cursor, working tree, and
retrieval instruction untouched. An absent entry is the normal first-install
case. Reuse the recorded cadence below unless the user requested a change.

**Do not reinvent this** — follow the packaged procedure:

```
memu-hermes docs task
```

In summary: settle a schedule with the user (default: every hour) and register a
recurring headless Hermes run through the **OS scheduler** — system cron on Unix,
or `memu-hermes schedule install` on Windows — with the prompt that document
gives you verbatim. It runs `memu-hermes prepare`, works through
`~/.memu/hosts/hermes/jobs/*.txt` in order, then `memu-hermes commit`. Do not use
Hermes's native `cronjob` for this task. The packaged task procedure first
removes every exact-name job an older guide created, and must stop rather than
add an OS task if that cleanup fails. Hermes already ships its CLI with the
client, so there is no separate CLI installation or authentication step.

### ✅ Verify Part 2

Confirm the crontab entry (Unix) or `memu-hermes schedule status` (Windows), then
dry-run: `memu-hermes prepare` (zero prepared sessions is fine and correct when
nothing is new).

---

## Part 3 — Patch `~/.hermes/SOUL.md` with the retrieval instruction

The *inject* seam: a standing instruction in Hermes's **SOUL.md** telling the
agent to pull relevant memory before answering. SOUL.md is the one file Hermes
loads from `HERMES_HOME` into every session regardless of working directory, so
the instruction is simply always there. (Project-level `.hermes.md`/`AGENTS.md`
files would miss sessions started elsewhere.)

**Do not hand-write the instruction.** memU owns the text and installs it:

```
memu-hermes install-instruction
```

One command, one file: it writes the full retrieval procedure — the `retrieve`
command to run and how to read the layers that come back — **inline** into a
marked block in `SOUL.md`, so it is present on every turn.

It does **not** install a skill. Hermes has a skills directory, but skills there
are pull-on-demand: the agent only sees a skill's body after calling
`skills_list`/`skill_view`, and only a relevance-selected subset surfaces per
turn — so a "retrieve before every turn" skill is not reliably surfaced, and a
SOUL.md *pointer* at it would silently no-op. Keeping the procedure inline avoids
that. (Skill-based hosts — Codex, Claude Code, OpenClaw — surface skill
descriptions every turn, so they install a short pointer plus a skill instead.)

`SOUL.md` is the *user's*, so it appends rather than overwrites (previous content
is backed up to `~/.hermes/SOUL.md.bak`), and memU's text sits in a marked block
that a re-run — or a later memU release — replaces in place. `--dry-run` shows the
diff without writing; `--path` targets a non-default home.

### ✅ Verify Part 3

```
cat ~/.hermes/SOUL.md
memu-hermes retrieve "smoke test"
```

The memU block must appear exactly once and carry the `memu-hermes retrieve`
command inline, anything the user had in `SOUL.md` must be intact, and `retrieve`
must exit cleanly (empty lists are fine). A fresh Hermes session is what picks up
the new SOUL.md.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-hermes` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-hermes report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-hermes report error --stage install --detail "<a full account of what went wrong>"
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

Report back to the user: the selected mode and its cloud endpoint or local store/provider; the scheduled job and its
schedule in words; and that the retrieval instruction is now in
`~/.hermes/SOUL.md`, carrying the `memu-hermes retrieve` procedure inline and
taking effect next session. Record and inject both read `~/.memu/config.env`, so
they provably share one store.
