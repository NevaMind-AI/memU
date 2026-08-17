# Install memU for Cursor

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

Installing memU on Cursor is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent Cursor
   agent sessions into durable memory (the *record* seam).
3. **Patch `AGENTS.md`** — a standing instruction that tells the agent to pull
   relevant memory before answering (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

**Scope note.** This adapter reads the **Cursor Agent** transcripts under
`~/.cursor/projects/` — the CLI (`cursor-agent`) and background agents. The IDE's
Composer chat history lives inside the editor's own SQLite state (`state.vscdb`)
and is not mined.

---

## Part 1 — Install memU

```
pip install memu-cli
```

This puts `memu` and **`memu-cursor`** on `PATH`. Confirm: `memu-cursor --help`.
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
memu-cursor doctor
```

It prints the resolved mode plus its endpoint or local store/provider and must
exit cleanly. Zero hits on the smoke-test retrieval is expected on a new
backend.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that mines recent transcripts under
`~/.cursor/projects/*/agent-transcripts/` into memU memory, skills, and
resources. In cloud mode, workspace resources are submitted but are not
currently persisted.

### 2.0 Prerequisite — the standalone `cursor-agent` CLI

The scheduled entry invokes **`cursor-agent -p` from a bare, non-interactive
environment**, and the **Cursor IDE does not provide that binary** — the CLI
is a separate install (the scope note above draws the same line: only the
CLI's transcripts are minable).

**Do not mistake the IDE's `cursor` launcher for it — on any OS.** The
editor puts a `cursor` shim on `PATH` everywhere (`resources/app/bin/cursor`
inside the install: `cursor.cmd` on Windows, the "install `cursor` command"
symlink on macOS, `/usr/bin/cursor` from Linux packages — the same pattern
as VS Code's `code`) that looks alive: `cursor -v` prints a
three-line `<version> / <commit> / <arch>`. It opens the GUI and has no
headless mode — `cursor -p` answers "Warning: 'p' is not in the list of known
options, but still passed to Electron/Chromium". Field data: a Windows
install stalled exactly here, `cursor` resolving while `cursor-agent` was
absent. Probe `cursor-agent`, never `cursor`.

**And the opposite trap right after installing on Windows: a stale
environment says "absent" while it is installed.** The native installer
lands the CLI in `%LOCALAPPDATA%\cursor-agent` and adds that directory to
the *user* `PATH` in the registry — but every process started before that
(the Cursor IDE, its integrated terminal, you) keeps its launch-time
environment, and any shell you spawn inherits the same staleness, so bare
`cursor-agent` stays not-found in this session. Field data, same machine as
above: an in-IDE probe concluded "not installed" while
`%LOCALAPPDATA%\cursor-agent\cursor-agent.cmd --version` answered fine. On a
"not found", check the registry user `PATH` and the landing dir before
re-installing; verify by full path; then have the user restart Cursor (or
open a terminal from a fresh Explorer context) before trusting the
bare-name check. The same staleness class exists on macOS/Linux with
different plumbing — the installer appends `~/.local/bin` to the shell rc,
terminals opened earlier never re-read it, and macOS's default `PATH` does
not include `~/.local/bin` at all — so there too, judge by the landing dir,
never by a pre-install shell. The gate below is immune on every OS by the
same move: it names the install locations explicitly instead of trusting
the session `PATH`.

Two checks before you register anything:

1. **`cursor-agent` resolves on `PATH`.** If it does not, install it with the
   user via Cursor's official installer —
   `curl https://cursor.com/install -fsSL | bash` on macOS / Linux / WSL, or
   `irm 'https://cursor.com/install?win32=true' | iex` on native Windows
   (typical Unix landing path `~/.local/bin`; confirm with
   `command -v cursor-agent`).
2. **It authenticates headless.** On a machine where the Cursor IDE is
   already signed in, the CLI picks up that account session — no separate
   login needed (field-tested). Otherwise log it in once with the user
   (`cursor-agent login`, or `CURSOR_API_KEY` — a Cursor account key, not a
   model-provider key). Know what the credential buys: the CLI runs
   **account-billed models through Cursor's backend**, and the IDE's custom
   base-URL / bring-your-own-key models do **not** carry over (field-tested:
   a custom-provider model configured in the GUI is not usable from
   `cursor-agent`). Agent runs therefore consume the account's plan quota —
   a green gate on a free plan can still starve at run time, the one
   entitlement failure the gate below cannot see. A user on provider-only
   credentials with no Cursor plan cannot run this record seam: for them
   this host is **retrieval-only** (Part 3; the IDE's own agent serves it,
   on whatever key the IDE uses) — their record seam belongs to a host they
   actually run headless, writing to the same shared store.

Prove both from a bare environment (keep `HOME` — the credential lives under
it, and real schedulers set it) before registering:

```
env -i HOME="$HOME" PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" cursor-agent -p 'ping'
```

This `PATH` is only a **probe** for common install locations. The cron entry
still derives its own `PATH` at registration time from
`command -v memu-cursor` / `command -v cursor-agent` (see `docs task`); a green
probe does not replace that line. On native Windows there is no `env -i`
form and you do not gate by hand: `memu-cursor schedule install` (the
registration path there — `docs task` has the section) runs the presence and
auth gates itself, with `--trust` baked in, and refuses with copy-paste
guidance if either fails. Just run it from a **newly opened** terminal — a
shell started before the CLI install keeps a stale `PATH` (the trap above).

Do not continue until the gate passes.

**Refresh an existing bridging registration before continuing.** If a memU
bridging entry exists, record its current cadence and remove **only that entry**.
On Unix, identify it by `~/.memu/hosts/cursor/bridge.sh` or an old inline
`cursor-agent -p 'Run the memU bridging pipeline. …'` prompt, then rewrite cron
with `crontab -l | grep -vE '{{task_name_pattern}}|hosts/cursor/bridge\.sh|memU bridging pipeline' | crontab -`.
Remove its `PATH=` line only if nothing else needs it, and use `crontab -r` only
when no lines remain. On Windows run `memu-cursor schedule uninstall`. Verify
`crontab -l` has no memU bridging entry while unrelated entries remain; on
Windows, `memu-cursor schedule status` must report not registered. Leave the
store, session cursor, working tree, and retrieval instruction untouched. An
absent entry is the normal first-install case. Reuse the recorded cadence below
unless the user requested a change.

**Do not reinvent this** — follow the packaged procedure:

```
memu-cursor docs task
```

In summary: settle a schedule with the user (default: every hour) and
register a cron entry that runs `cursor-agent -p "<the prompt that document gives
you verbatim>"` — the prompt runs `memu-cursor prepare`, works through
`~/.memu/hosts/cursor/jobs/*.txt` in order, then `memu-cursor commit`. Nothing in
it is machine-specific. On Windows, that document's Task Scheduler section
applies instead: `memu-cursor schedule install`, never a hand-written entry.

### ✅ Verify Part 2

Confirm the cron entry (Unix) or `memu-cursor schedule status` (Windows), then
dry-run: `memu-cursor prepare` (zero prepared sessions is fine and correct when
nothing is new).

---

## Part 3 — Patch `AGENTS.md` with the retrieval instruction

The *inject* seam. Cursor's Agent reads `AGENTS.md` from the **project root** —
there is no global user-level instruction file the CLI honors (the IDE's User
Rules live in editor settings, out of reach here). So the instruction is
installed **per project**:

```
cd <the project> && memu-cursor install-instruction
```

It writes memU's block into `./AGENTS.md`, creating the file if absent, and
prints the diff. It appends rather than overwrites (existing content is backed up
to `AGENTS.md.bak`), and it is idempotent: the text sits in a marked block that a
re-run — or a later memU release — replaces in place. `--dry-run` shows the diff
without writing; `--path` targets another file.

Repeat for each project that should retrieve from memU, and tell the user that a
new project needs this one command run once.

### ✅ Verify Part 3

```
cat AGENTS.md
memu-cursor retrieve "smoke test"
```

The memU block must appear exactly once, prior content intact, and `retrieve`
must exit cleanly (empty lists are fine). A fresh Cursor session picks up the new
AGENTS.md.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-cursor` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-cursor report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-cursor report error --stage install --detail "<a full account of what went wrong>"
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
schedule in words; which projects got the `AGENTS.md` instruction. Record and
inject both read `~/.memu/config.env`, so they provably share one backend.
