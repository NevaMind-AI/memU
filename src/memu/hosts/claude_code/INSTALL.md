# Install memU for Claude Code

> **Audience: the agent.** A user will point you at this file ("follow this guide
> to install memU"). Work top to bottom. Each part ends with a **verify** gate —
> do not proceed until the current one passes.
>
> Everything on the memU side is a `PATH` command; you should never need to write
> an absolute path to a script.

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
"sched task: " + [bool](Get-ScheduledTask -TaskPath '\memU\' -TaskName 'memu-bridging-claude-code' -ErrorAction SilentlyContinue)
"inject:     " + [bool](Select-String -Path "$env:USERPROFILE\.claude\CLAUDE.md" -Pattern 'memu' -Quiet -ErrorAction SilentlyContinue)
```

macOS / Linux:

```
command -v claude || echo "claude NOT FOUND (landing dir: $(ls ~/.local/bin/claude 2>/dev/null || echo none))"
command -v memu-claude-code || echo "memu NOT FOUND - do Part 1"
[ -f ~/.claude/.credentials.json ] && echo "cred file: yes" || echo "cred file: no"
crontab -l 2>/dev/null | grep -qE 'ANTHROPIC|CLAUDE_CODE' && echo "cron env: set" || echo "cron env: none"
crontab -l 2>/dev/null | grep -q 'memU bridging pipeline' && echo "cron entry: yes" || echo "cron entry: no"
grep -q memu ~/.claude/CLAUDE.md 2>/dev/null && echo "inject: yes" || echo "inject: no"
```

Reading the answers: `memu` missing → Part 1. `claude` missing → Part 2.0
step 1. No credential anywhere → Part 2.0 step 2. No task / cron entry →
Part 2 registration. `inject` false → Part 3. Everything present → verify
gates only; there is nothing to install.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. A Python runtime is required
regardless, because the bridging task runs Python.

### 1.1 Install

```
pip install memu-cli
```

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

Write them to **`~/.memu/config.env`**, which every memU command loads. Use an
**absolute** path for `MEMU_DB`, and `chmod 600` the file (the key is plaintext —
tell the user). Do **not** instead export these in a shell profile: the scheduled
task does not inherit your interactive shell.

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
memu-claude-code doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** on a new store.

---

## Part 2 — Register the bridging (record) task

The *record* seam: a scheduled job that periodically mines recent sessions under
`~/.claude/projects` into memU memory, skills, and resources. In cloud mode,
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

## Done

Report back to the user: the selected mode and its cloud endpoint or local store/provider; the scheduled
job and its schedule in words; and that the retrieval instruction is now in
`~/.claude/CLAUDE.md`, pointing at the `memu-retrieve` skill and taking effect in
their next session. Record and inject both read `~/.memu/config.env`, so they provably share one backend — what the task learns tonight is what retrieval finds tomorrow.
