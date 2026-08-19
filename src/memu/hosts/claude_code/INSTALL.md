# Install memU for Claude Code

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

Installing memU on Claude Code is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register the bridging task** — the scheduled job that turns recent Claude
   Code sessions into durable memory (the *record* seam).
3. **Patch `~/.claude/CLAUDE.md`** — a standing instruction that tells you to pull
   relevant memory before you answer (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

---

## Preflight — establish state in one shot

Partially-installed machines and re-runs are the common case. Run the one
block for this OS, read the answers, and do only the parts still missing.
**Never search the filesystem for binaries** — resolution is `Get-Command` /
`command -v` plus the one known landing directory; a recursive disk search
is always the wrong move (field data: it is where slow installs go to die).

Windows (PowerShell):

```
$c = Get-Command claude -ErrorAction SilentlyContinue
"claude:     " + $(if ($c) { $c.Source } else { "NOT FOUND; landing dir has it: $(Test-Path "$env:USERPROFILE\.local\bin\claude.exe") (True = stale PATH - prepend the landing dir to PATH for the next commands)" })
"memu:       " + $(if (Get-Command memu-claude-code -ErrorAction SilentlyContinue) { "ok" } else { "NOT FOUND - do Part 1" })
"credential: token=" + [bool][Environment]::GetEnvironmentVariable('CLAUDE_CODE_OAUTH_TOKEN','User') + " apikey=" + [bool][Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User') + " file=" + (Test-Path "$env:USERPROFILE\.claude\.credentials.json")
if (Get-Command memu-claude-code -ErrorAction SilentlyContinue) { memu-claude-code schedule status } else { "sched task: check after Part 1" }
"inject:     " + [bool](Select-String -Path "$env:USERPROFILE\.claude\CLAUDE.md" -Pattern 'memu' -Quiet -ErrorAction SilentlyContinue)
```

macOS / Linux:

```
command -v claude || echo "claude NOT FOUND (landing dir: $(ls ~/.local/bin/claude 2>/dev/null || echo none))"
command -v memu-claude-code || echo "memu NOT FOUND - do Part 1"
[ -f ~/.claude/.credentials.json ] && echo "cred file: yes" || echo "cred file: no"
crontab -l 2>/dev/null | grep -qE 'ANTHROPIC|CLAUDE_CODE' && echo "cron env: set" || echo "cron env: none"
crontab -l 2>/dev/null | grep -qE '{{task_name_pattern}}|hosts/claude-code/bridge\.sh|memU bridging pipeline' && echo "cron entry: yes" || echo "cron entry: no"
grep -q memu ~/.claude/CLAUDE.md 2>/dev/null && echo "inject: yes" || echo "inject: no"
```

Reading the answers: `memu` missing → Part 1. `claude` missing → Part 2.0
step 1. No credential anywhere → Part 2.0 step 2. `inject` false → Part 3.
Part 2 always runs once its prerequisites pass: an existing task / cron entry
must be removed and recreated from the current packaged procedure, not treated
as proof that its prompt and wrapper are current.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. A Python runtime is required
regardless, because the bridging task runs Python.

### 1.1 Install

```
pip install --upgrade memu-cli
```

**`--upgrade` matters, and a bare install is not enough.** A machine that
already carries an older `memu-cli` keeps it otherwise, and this guide names
subcommands (`init`, `config`) that older builds answer with `invalid choice`.
If you meet that error anywhere below, you are on a stale build: upgrade, then
re-run the command that failed.

This puts `memu` (the library's own surface) and **`memu-claude-code`** (the
Claude Code adapter) on `PATH`. Both Part 2 (record) and Part 3 (inject) go
through `memu-claude-code`.

Confirm it resolves:

```
memu-claude-code --help
```

If it is not found, the install landed in an environment that isn't on your
`PATH`. Fix that now — the scheduled task in Part 2 runs from a bare,
non-interactive environment and needs this command to resolve there.

### 1.2 Configure the memory backend

**Never write `~/.memu/config.env` by hand.** No heredoc, no `echo >>`, no
editor. Every memU host on this machine shares that one file, it holds a
plaintext credential, and it carries an invariant a text edit cannot keep:
record and retrieval must agree on one backend — and in local mode on one store
and one embedding space — or retrieval keeps succeeding and finds nothing.
`memu-claude-code config` is the writer: it merges (anything it is not
given is left alone, including comments and another host's settings), sets
the file's permissions, and refuses the edits that break retrieval silently.

**Came from memU's `SKILL.md`? You already ran `init`** — it created the file
and, if the user handed over a memU Cloud key, already selected cloud memory.
Read the state below rather than assuming which.

If you came straight to this guide instead, run it now:

```
memu-claude-code init --cloud-api-key <the user's memU key>
```

Bare `memu-claude-code init` if the user has no key, or would rather keep
memory on this device. Re-running is harmless either way — `init` is idempotent
and keeps a mode it already finds. One caveat: passing a key selects **cloud**,
and on a machine already using local memory that is a switch. Nothing is
deleted, but memories written locally stop being retrieved; `init` warns and
proceeds — so if you are unsure what this machine already uses, read the state
first and say what the switch costs before you pass a key.

Reading the state writes nothing:

```
memu-claude-code config show
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
memu-claude-code config --cloud --cloud-api-key <memu-api-key>
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
memu-claude-code config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
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
memu-claude-code config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-base-url http://localhost:11434/v1 --embed-model nomic-embed-text --embed-api-key local
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
memu-claude-code config --local --embed-base-url http://127.0.0.1:11434/v1
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
memu-claude-code doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** on a new store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that periodically mines recent sessions under
`~/.claude/projects` into memU memory, skills, and resources. On Windows it also
mines discovered Cowork `local_*/audit.jsonl` workspaces through this same task;
there is no second schedule or memory store. In cloud mode,
workspace resources are submitted but are not currently persisted.

### 2.0 Prerequisite — a standalone, headless-authenticated `claude`

The scheduled run invokes **`claude -p` from a bare, non-interactive
environment**. The Claude **Desktop app cannot serve it**: its bundled binary
lives outside `PATH` and its login is invisible to the standalone CLI
(memU#538). Two checks, in order, before you register anything:

1. **`claude` resolves on `PATH`.** If it does not, install it — **do not
   ask which installer**: announce what you are about to run, then run the
   official install script (it lands in `~/.local/bin`, needs no elevation
   and no node):
   - Windows: `irm https://claude.ai/install.ps1 | iex`
   - macOS / Linux: `curl -fsSL https://claude.ai/install.sh | bash`

   `winget install Anthropic.ClaudeCode` and
   `npm install -g @anthropic-ai/claude-code` are fallbacks — for when the
   script fails, or the user has already stated a preference. Never install
   silently as a side effect of scheduling, and never offer "skip" — here,
   or anywhere in this section: an unregistered record seam is a failed
   install, not an outcome to pick from a menu.
2. **It authenticates headless, on a *persistent* credential.** **Probe
   before you ask — always, wherever this guide is running.** Run the gate
   below first: an existing credential (a prior CLI login, an
   already-persisted variable) serves headless runs without any new setup,
   and the gate result is the only fact that matters. Green = this step is
   already done. Only on a failing gate, ask the user to pick one of
   **exactly these two** — never improvise more options, and never offer
   "skip": an unauthenticated record seam is a failed install, not a
   variant of success.
   - **Web auth** (in a browser) — **recommended**: `claude setup-token` —
     a browser sign-in; on success the CLI is **authenticated directly**
     (the credential lands in the profile — nothing to copy, no variable
     to set). Requires a Claude subscription — it refuses without one; do
     not loop on it, move down the list.
   - **Anthropic API key** (platform account, pay per token): persist
     `ANTHROPIC_API_KEY`.

   The host's question UI may append its own free-text **"Other"** choice
   to any question — that is the UI's escape hatch, not a third method,
   and an answer typed through it does not reopen the menu: an API key
   pasted there *is* the API-key option; a custom endpoint is the removed
   trap below — explain and re-offer the two; anything else is "neither".

   If the user has neither, **stop here and say so**: Part 2 is blocked on
   an unmet prerequisite — Parts 1 and 3 still stand, and the user knows
   exactly what to bring back. Never register a schedule that cannot
   authenticate. And no third options: a "custom endpoint" invites a
   protocol trap (the CLI speaks the Anthropic Messages protocol, which
   OpenAI-format relays do not serve), and "skip" is failure wearing a
   menu label.

   **Web auth is interactive — run it start-to-finish, and never in a
   captured or background shell.** `setup-token` opens the browser and
   listens on a localhost callback port *inside the terminal process*; if
   you kill that process and tell the user to "just log in", they sign in
   and land on an unreachable `localhost:…/callback` page whose code is
   bound to the dead run and unusable — field data: exactly this strand.
   What works, end to end:
   1. Launch it in a **real terminal window on the user's desktop** and
      leave it running (Windows: `Start-Process claude -ArgumentList
      'setup-token'`; on macOS/Linux run it in the user's visible
      terminal) — do not hand the user a bare "open a terminal and run
      this" instruction.
   2. Before they click anything, tell them exactly what they will see:
      the browser opens → sign in → click **Authorize** → the browser
      shows the success page ("Build something great — You're all set up
      for Claude Code. You can now close this window."). The terminal
      window finishes by itself and **Claude Code is signed in directly**
      — nothing to copy, nothing to paste, no variable to set.
   3. Then offer exactly two continuations — as a **selectable choice**
      (the host's option UI), never a free-text "let me know":
      - **Continue** (login succeeded) — run the gate below immediately
        and **show the user the result** ("headless login verified —
        prerequisite complete") before going straight to registration in
        the same session. Never end the turn leaving the user unsure
        whether the install finished.
      - **Another way** — the login did not work, or the user changed
        their mind: fall back to the **Anthropic API key** option.
   4. Do not stop at "tell me when you're done": the credential file
      appears in the profile when the flow truly succeeds — watch for it,
      and treat it as the "Continue" signal if the user has wandered off.
      If the browser shows an unreachable `localhost:…/callback` page,
      the terminal process died — close that tab and relaunch from
      step 1; never try to salvage the code in the URL.
   5. **Browser shows the success page but the gate still says "Not
      logged in"? That is the split-proxy trap** (field data) — do not
      hunt the filesystem or the credential manager for a token that was
      never written. The user's browser reaches Anthropic through a
      proxy, but the terminal process has none, so the CLI half of the
      OAuth exchange fails even though the browser half looks complete.
      Fix it where it lives, then rerun: in that terminal window,
      `set HTTPS_PROXY=http://127.0.0.1:<port>` (and `HTTP_PROXY`
      likewise), then `claude setup-token` again. The scheduled run needs
      the same outbound — persist the proxy variables exactly like a
      credential (Windows `setx`; Unix crontab header), and keep Part 1's
      `NO_PROXY` note in mind for loopback embedding servers. **Only the
      gate decides success — never the browser page.**

   Persisting the API key (Web auth needs none of this — its credential
   is the profile file): on Windows, `setx` (the S4U task reads persistent
   user env); on macOS/Linux a shell-profile `export` does **not** reach
   cron —
   the variables go in the crontab header exactly like the `PATH` line. A
   key exported only in the current shell passes your check here and still
   leaves the scheduled task stuck on "Not logged in" — the one false
   positive this gate cannot catch by itself. The gate below proves
   whichever method was chosen — with the probe carrying that method's own
   variables, and nothing else.

**Right after installing, expect a stale-`PATH` false negative.** On
Windows the installers register `claude` on the *user* `PATH` in the
registry; on macOS/Linux they append to the shell rc — and in both cases
every process started before the install, this shell included, keeps its
launch-time environment, so `claude` can report "not found" here while
being correctly installed (the mechanism is field-proven on this repo's
cursor host). Judge by the landing directory (`~/.local/bin`) or a **newly
opened** terminal, never by a pre-install shell. The gate below is immune —
it names the install locations explicitly. On Windows, run
`schedule install` the same unconditional way — with the landing directory
prepended to that one command's `PATH`:

```
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"; memu-claude-code schedule install
```

This is a no-op in a fresh shell and the fix in a stale one — there is no
need to know which this is — and it is safe either way: the registered
task bakes absolute paths and never depends on the invoking shell.

Prove both the way the scheduler will experience them — from a bare
environment, resolve *and* authenticate. The probe must carry **exactly
what the scheduler will carry, nothing more** — which differs by method:

- **Web auth** — the credential lives in a file under `HOME`, so keeping
  `HOME` is enough (real schedulers set it):

  ```
  env -i HOME="$HOME" PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" claude -p 'ping'
  ```

- **Anthropic API key** — the credential is an environment variable, and
  `env -i` strips it: the bare probe above would **false-fail a correctly
  configured machine**. Name the variable in the probe with its value,
  exactly as the crontab header will carry it:

  ```
  env -i HOME="$HOME" PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" ANTHROPIC_API_KEY="<the key>" claude -p 'ping'
  ```

This `PATH` is only a **probe** for the common install locations. The cron
entry still derives its own `PATH` at registration time from
`command -v memu-claude-code` / `command -v claude` (see `docs task`); a green
probe does not replace that line.

On Windows, `schedule install` (reached through `docs task` below) runs this
gate for you and refuses with install guidance when either check fails. Do
not continue until the gate passes.

**Refresh an existing bridging registration before continuing.** If a memU
bridging entry exists, record its current cadence and remove **only that entry**.
On Unix, identify the cron or launchd entry by
`~/.memu/hosts/claude-code/bridge.sh` or an old inline
`claude -p 'Run the memU bridging pipeline. …'` prompt. Rewrite cron with
`crontab -l | grep -vE '{{task_name_pattern}}|hosts/claude-code/bridge\.sh|memU bridging pipeline' | crontab -`;
remove its `PATH=` line only if nothing else needs it, and use `crontab -r` only
when no lines remain. For launchd, run `launchctl bootout gui/$(id -u)/{{task_name}}`
and delete only its memU plist. On Windows run
`memu-claude-code schedule uninstall`. Verify `crontab -l` (and
`ls ~/Library/LaunchAgents`, if launchd was used) shows no memU bridging entry
while unrelated entries remain; on Windows, `memu-claude-code schedule status`
must report neither the current nor legacy task registered. Leave the store,
session cursor, working tree, and retrieval instruction untouched. An absent entry is the normal first-install
case. Reuse the recorded cadence below unless the user requested a change.

**Do not reinvent this.** Follow the packaged procedure:

```
memu-claude-code docs task
```

It is authoritative. In summary: you will settle a schedule with the user
(default: every hour) and register a recurring headless Claude Code run —
via system cron (the default; launchd only if the user prefers it) invoking
`claude -p "<the prompt that document gives you verbatim>"` — that runs
`memu-claude-code prepare`, works through
`~/.memu/hosts/claude-code/jobs/*.txt` in order, then runs
`memu-claude-code commit`.

Nothing in that prompt is machine-specific. If you find yourself substituting an
absolute path into it, you are doing it wrong.

### ✅ Verify Part 2

Confirm the cron/launchd entry exists. Then dry-run the first step by hand:

```
memu-claude-code prepare
```

It should report how many sessions it prepared (zero, if there is nothing new
since the cursor — that is fine and correct).

---

## Part 3 — Patch `~/.claude/CLAUDE.md` with the retrieval instruction

The *inject* seam: a standing instruction in Claude Code's **global memory file**
telling you to pull relevant memory before you answer. Claude Code loads
`~/.claude/CLAUDE.md` into every session in every project, so the instruction is
simply always there — no hook, no wrapper, no per-turn process.

**Do not hand-write the instruction.** memU owns the text and installs it for you:

```
memu-claude-code install-instruction
```

One command, two files, because Claude Code has skills:

- `~/.claude/skills/memu-retrieve/SKILL.md` — the procedure: the `retrieve`
  command to run and how to read the layers that come back. This directory is
  memU's own, so a re-run overwrites it whole.
- `~/.claude/CLAUDE.md` — two sentences telling you to use that skill before
  answering. The detail stays out of here on purpose: this file is in context on
  every turn, whether or not the turn touches memory; the skill is loaded only
  when you act on it.

It creates either file if absent and prints the diff of both. `CLAUDE.md` is the
*user's*, so it appends rather than overwrites (previous content is backed up to
`~/.claude/CLAUDE.md.bak`), and memU's text sits in a marked block that a re-run —
or a later memU release — replaces in place. `--dry-run` shows the diffs without
writing; `--print` prints what would be installed.

### ✅ Verify Part 3

```
cat ~/.claude/CLAUDE.md
cat ~/.claude/skills/memu-retrieve/SKILL.md
memu-claude-code retrieve "smoke test"
```

The memU block must appear exactly once and name the `memu-retrieve` skill, that
skill must exist, anything the user had in `CLAUDE.md` must be intact, and
`retrieve` must exit cleanly (empty result lists are fine). A *fresh* Claude Code
session is what picks up the new CLAUDE.md and skill — do not be surprised that
neither is in your own context yet.

---

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Close this run with
**one** command, whichever way it ended.

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-claude-code` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-claude-code report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

**You are stopping early instead** — a part that failed, or a prerequisite you
could not resolve — then tell the user as usual:

```
memu-claude-code report error --stage install --detail "<a full account of what went wrong>"
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

Report back to the user: the selected mode and its cloud endpoint or local store/provider; the scheduled
job and its schedule in words; and that the retrieval instruction is now in
`~/.claude/CLAUDE.md`, pointing at the `memu-retrieve` skill and taking effect in
their next session. Record and inject both read `~/.memu/config.env`, so they provably share one backend — what the task learns tonight is what retrieval finds tomorrow.
