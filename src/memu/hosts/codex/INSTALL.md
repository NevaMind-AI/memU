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
pip install memu-cli
```

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

Write them to **`~/.memu/config.env`**, which every memU command loads:

```
MEMU_DB=/Users/<you>/.memu/memu.sqlite3
MEMU_MEMORY_MODE=local
MEMU_EMBED_PROVIDER=openai
MEMU_API_KEY=<key or env-var name>
```

Use an **absolute** path for `MEMU_DB`. A relative one resolves against the
working directory, and the scheduled task has no reliable working directory.

> Do **not** instead export these in a shell profile. The scheduled task does not
> inherit your interactive shell. The file is the carrier; a profile export is
> not. (A `MEMU_*` variable that *is* set in the environment wins over the file,
> so you can still override for one command.)

The API key sits in plaintext in this file. Tell the user, and set the
permissions: `chmod 600 ~/.memu/config.env`.

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
memu-codex doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** — the store is new; you
are testing that config resolves and the store answers, not that it has content.

If it errors, fix `~/.memu/config.env` before continuing. Both later parts depend
on this working, and both fail *silently* if it is wrong.

---

## Part 2 — Register the bridging (record) task

The *record* seam: an OS-scheduled, non-interactive `codex exec` run that
periodically mines recent `~/.codex/sessions` into memU memory, skills, and
resources. In cloud mode, workspace resources are submitted but are not
currently persisted.

### 2.0 Prerequisite — a standalone `codex` CLI

The scheduled run invokes `codex exec` from a bare, non-interactive
environment. Two checks, in order, before you register anything:

1. **`codex` resolves on `PATH`.** If it does not, install it — **do not ask
   which installer**: announce what you are about to run, then run the official
   install script (it lands in `~/.local/bin`, needs no elevation and no Node):
   - Windows: `irm https://chatgpt.com/codex/install.ps1 | iex`
   - macOS / Linux: `curl -fsSL https://chatgpt.com/codex/install.sh | bash`

   `npm install -g @openai/codex` is a fallback — for when the script fails, or
   the user has already stated a preference. Never install silently as a side
   effect of scheduling, and never offer "skip": an unregistered record seam is
   a failed install, not an outcome to pick from a menu.
2. **It is signed in for that account.** Codex CLI reuses profile authentication
   (normally `~/.codex/auth.json`), including authentication established through
   Codex Desktop. There is no separate headless-token setup step here. If that
   profile is not signed in, use the normal Codex sign-in flow before continuing.

Open a new terminal after the install, since the current shell's `PATH` may
predate it, then continue only when `codex --version` succeeds.


**Do not reinvent this and do not create a ChatGPT/Codex native task.** Follow
the packaged procedure:

```
memu-codex docs task
```

It is authoritative. It first migrates any task created by the legacy native
scheduler guide, using Codex Desktop's task-management surface and stopping on
any ambiguous listing or deletion. Only after that gate passes does it register
the replacement with cron/launchd on Unix or the shared
`memu-codex schedule` helper on Windows. The OS wrapper keeps the prompt in a
file, runs `codex exec` with the fixed unattended-automation flags, and appends
stdout/stderr to `~/.memu/hosts/codex/bridge.log`.

This is a scheduling migration, not an uninstall. Pending jobs, session
manifests, memory/skill mirrors, the retrieval instruction, configuration, and
the store all stay in place for the first OS run to continue.

### ✅ Verify Part 2

Confirm **both** sides of the migration:

1. Codex Desktop's native scheduled-task list has no approved legacy memU
   bridging task. If it could not be enumerated or removed unambiguously, Part 2
   has failed and no OS task should exist.
2. The OS scheduler has exactly one canonical Codex bridging task: the wrapper
   entry documented by `memu-codex docs task` on Unix, or
   `\memU\memu-bridging-codex` (`memu-codex schedule status`) on Windows.

Then run one task through the scheduler itself. Verify `bridge.log` grew and
that the session manifest / `jobs/` timestamps moved; an interactive
`memu-codex prepare` is not a substitute for the scheduler's account, sparse
environment, and working directory. Report the scheduler, task identity,
schedule, legacy migration outcome, and first-run evidence back to the user.

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
