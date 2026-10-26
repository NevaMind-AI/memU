# Install memU for Codex

<!-- memu-codex-record: submit-v1 -->
<!-- memu-codex-permissions: v22 -->

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

## Installation progress — five stages

Use English for installation guidance unless the user explicitly requests
another language. Begin directly with stage 1, even when permissions are blocked.
Render each stage message below as a Markdown `##` heading exactly once before its work. Within a stage, use
at most one short plain-text status when needed; never repeat the emoji, counter
or stage name in status updates. Show a concrete blocker and next action briefly,
without narrating commands, process details or reasoning.

| Stage message | Work |
| --- | --- |
| 🔐 [1/5] Checking installation permissions | Full-access gate below |
| 📦 [2/5] Preparing memU and the memory backend | Part 1; reuse existing configuration |
| 🔔 [3/5] Setting up automatic memorization | Part 2 prerequisite; Part 3 dual-hook registration; old-schedule handoff if needed |
| 🧠 [4/5] Setting up memory retrieval | Part 3 registration and trust |
| 🚀 [5/5] Starting your first memorize task | Finish legacy cleanup and invite the next user message |

Installation is complete once the backend check, Submit hook registration,
prompt-hook registration/trust and M3 cleanup pass. Print
`✅ memU installation complete` and Part 2's activation message. The first
user-triggered retrieval and memorize run is a post-install check, not a
completion gate. Report actual configuration or cleanup blockers when present.

## Execution permissions — Full access before installation

Before package installation, `init`, setup or migration changes, inspect the
current session's actual sandbox mode. Continue only with `danger-full-access`.
Approval policy is separate: `approval_policy = never` does not establish Full
access. If sandbox mode is not provided, say that you cannot confirm it and ask
the user to check the setting.

If the session is restricted or its mode is unknown, pause at stage 1 and show
**both** options below so the user can choose. Bold only the application name,
placing the colon outside the bold markers, e.g. `**Codex Desktop**: ...` or
`**Codex Desktop**：切换……`:

- **Codex Desktop**: ask the user to switch to **Full access / 完全访问权限**
  and reply "continue installation" here. Recheck the effective mode before
  resuming; remain paused if the change has not taken effect.
- **Codex CLI**: ask the user to exit and start a new session from the same
  directory, then repeat the installation request:

  ```sh
  codex --dangerously-bypass-approvals-and-sandbox
  ```

  The flag disables sandboxing and approval prompts for that session. After
  installation, exit and launch Codex normally to restore the usual restrictions.

Always show both instructions; do not infer Desktop versus CLI from session
metadata or installed binaries. Do not switch modes or change Windows ACLs
yourself. Normal OS permissions still apply. If the execution helper fails
before a command starts (for example, `setup refresh had errors`), stop
alternate-shell, Node and computer-use retries and show both access instructions.
If already in Full access,
report the executor startup failure and ask the user to restart Codex; the bypass
flag is not evidence that the underlying failure will be fixed.


## Choose the installation path

**New installation:** follow Parts 1–3 below.
**Existing installation:** start with **Existing installations — migration**
later in this same guide. It references the setup parts for the new entries and
owns old schedule/skill cleanup. Read this guide once; no additional docs command
is needed.

New installation has three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Verify the standalone CLI** — turn recent
   Codex sessions into durable memory (the *record* seam).
3. **Register and trust `UserPromptSubmit`** — retrieve memory asynchronously
   on each user submission (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

## Submit record trigger (Codex)

The record trigger is UserPromptSubmit: a short handler launches prepare → headless `codex exec` → commit in the background without waiting for completion.
Follow Part 2 after the backend gate passes. Existing installations use the
migration section for safe handoff.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. There is no npm package — do not look
for one; a Python runtime is required regardless, because the bridging task runs
Python.

### 1.1 Install

Skip any installation, registration or check already completed in this run
unless its inputs or configuration have changed.

If you just installed or upgraded memu-cli, skip this step.
Otherwise, use the user's requested package manager and source. The default is:

```text
pip install --upgrade memu-cli
```

For uv, use `uv tool install --upgrade memu-cli`. Confirm `memu-codex --help`
succeeds once after installation. Keep the executable available to Codex's
background processes; respect any explicit executable path supplied by the user.


### 1.2 Configure the memory backend

**Never write `~/.memu/config.env` by hand.** No heredoc, no `echo >>`, no
editor. Every memU host on this machine shares that one file, it holds a
plaintext credential, and it carries an invariant a text edit cannot keep:
record and retrieval must agree on one backend — and in local mode on one store
and one embedding space — or retrieval keeps succeeding and finds nothing.
`memu-codex config` is the writer: it merges (anything it is not
given is left alone, including comments and another host's settings), sets
the file's permissions, and refuses the edits that break retrieval silently.

**Came from memU's `SKILL.md`? You already ran `init`** — it created the file
and, if the user handed over a memU Cloud key, already selected cloud memory.
Read the state below rather than assuming which.

If you came straight to this guide instead, run it now:

```
memu-codex init --cloud-api-key <the user's memU key>
```

Bare `memu-codex init` if the user has no key, or would rather keep memory on
this device. Re-running is harmless either way — `init` is idempotent and keeps
a mode it already finds. One caveat: passing a key selects **cloud**, and on a
machine already using local memory that is a switch. Nothing is deleted, but
memories written locally stop being retrieved; `init` warns and proceeds — so
if you are unsure what this machine already uses, read the state first and say
what the switch costs before you pass a key.

Reading the state writes nothing:

```
memu-codex config show
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
memu-codex config --cloud --cloud-api-key <memu-api-key>
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
memu-codex config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <key>
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
memu-codex config --local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-base-url http://localhost:11434/v1 --embed-model nomic-embed-text --embed-api-key local
```

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

**The existing config fails doctor? Repair the connection, never the identity.**
If `~/.memu/config.env` predates this install and `doctor` fails, diagnose the
transport first — is the embedding server running, is a proxy in the way — before
changing anything. A connection-level repair is an ordinary `config` call and is
allowed to land:

```
memu-codex config --local --embed-base-url http://127.0.0.1:11434/v1
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
memu-codex doctor
```

It prints the resolved mode plus its endpoint or local store/provider, and runs a smoke-test retrieval. It
must exit cleanly. **Zero hits is the expected result** — the store is new; you
are testing that config resolves and the store answers, not that it has content.

If it errors, fix it with another `memu-codex config` call — never by editing
`~/.memu/config.env` — before continuing. Both later parts depend
on this working, and both fail *silently* if it is wrong.

---

## Part 2 — Verify the background CLI prerequisite

The *record* seam starts on user prompt submission: prepare → headless `codex exec` →
commit. In cloud mode, workspace resources are submitted but not persisted.

### 2.0 Prerequisite — a standalone Codex CLI

Probe before installing: resolve `codex` and run `codex --version`. Reuse a
working CLI, including an existing npm-managed installation. If lookup fails,
check the official installer's landing directory before reinstalling; an older
shell may simply have a stale PATH.

If Codex is missing, announce the action and run the official native installer:

- Windows, from PowerShell:

  ```powershell
  irm https://chatgpt.com/codex/install.ps1 | iex
  ```

- macOS / Linux:

  ```sh
  curl -fsSL https://chatgpt.com/codex/install.sh | sh
  ```

These installers do not require Node.js or npm. Use an already available package
manager only as a fallback if the native installer fails or the user has stated
a preference; for existing npm environments, `npm install -g @openai/codex` is
supported. Do not install a second Node.js manager to install Codex. If download,
approval or installation fails, report the blocker and retain the old record
entry; do not register a callback whose agent cannot start.

After installation, resolve the actual executable and run its `--version`.
The current official default landing directories are:

- Windows: `$env:LOCALAPPDATA\Programs\OpenAI\Codex\bin`.
- macOS/Linux: `$HOME/.local/bin`.

Honor an explicit `CODEX_INSTALL_DIR` instead of these defaults. Prepend the
actual landing directory to the current install process's PATH before calling
`memu-codex install-prompt-hook`; a persistent PATH change does not refresh an already
running Desktop or its shells. Read the registered `--agent` back and require an
absolute path to the verified executable. Restart Desktop or open a fresh session
when necessary, then check the callback again.

Keep the existing Codex home, model/provider and authentication configuration.
Desktop and CLI normally share that configuration; reuse it before asking for
new credentials. A successful `--version` proves startup, while the real record
check below proves the configured execution path. If an existing CLI resolves
but cannot start, report and repair that failure before registration.

### 2.1 Register both Submit handlers in Part 3

After the CLI probe and Part 1's backend gate pass, continue to Part 3.
The installation command registers retrieval and background memorization together.
It preserves unrelated hooks and leaves Codex notify configuration unchanged.

### Runtime check — one CLI call

Before the short verification turn, record its start time (PowerShell:
`$since = [DateTimeOffset]::Now.ToUnixTimeSeconds()`). After the turn, run:

```text
memu-codex hook-status --since <start-time>
```

The command returns JSON with `retrieve.status`, `retrieve.exit_code`,
`memorize.status` and each log path. Exit 0 means retrieval succeeded (context or
empty result) and memorization either started, succeeded, or skipped normally
(`busy` / `cooldown`); exit 1 means retrieval or memorization failed; exit 2 means
evidence is pending. `worker_started` only means the worker launched; `started`
means it acquired the lock, passed cooldown and entered processing. `succeeded`
and `failed` report the pipeline result. A worker launch is not proof of processing.
Use this output directly instead of writing log parsers,
reading source code or enumerating processes. It does not wait or retrieve memory.
`cooldown` also includes `cooldown_until` (Unix seconds) and
`cooldown_remaining_minutes`, recalculated and rounded up when queried.
A zero remaining value means another submission may try again; it does not
schedule a run.

The time filter excludes logs started before the check; avoid concurrent test
turns, as the two newest logs are not correlated by session ID.

### ✅ Verify Part 2

Verify that the registered callback and agent paths exist. Runtime startup is
checked after the next user message; it does not delay cleanup or installation
completion. When installation and M3 cleanup are complete, include the following
meaning once in the final report, using the same language as the rest of that
report. This is a content example, not text to append verbatim:

> memU is installed. Send one more message here to trigger your first memory
> retrieval and background memorize task. You can ask: "What did memU retrieve
> for this message?" Memorization processes new conversation content in the
> background; follow its logs in `~/.memu/hosts/codex/log/hooks/memorize/`.

Resolve the directory to the user's actual local path. Use the existing
conversation unless Codex explicitly requires a new session. Do not claim a
worker is already running without startup evidence. If a later runtime check
finds an error, report it then; do not wait for jobs or worker completion.

---

## Part 3 — Register and trust both UserPromptSubmit hooks

This part owns the *inject* seam: Codex runs `memu-codex prompt-hook` with
`async: true` when the user submits a prompt. The command reads the hook's stdin
JSON, passes a query to shared retrieval, and returns
`hookSpecificOutput.additionalContext`. Codex starts its first model request
without waiting for retrieval and consumes completed hook context at a later
model-request boundary. Results may cause a follow-up response in the same turn;
if they arrive after the turn ends, they may be consumed on the next turn instead.
They cannot change a model request already in flight. Retrieval failures or
timeouts do not block the user's turn.

The independent `memorize-hook` handler launches the existing background worker and
returns after at most a half-second admission check, without waiting for processing.
It supplies an `additionalContext` status snapshot for the model to use only when
the user asks about memorization; ordinary replies need not mention it. The snapshot
includes its observation time, this worker's log path, and the outcome: `started`
(processing began; completion unconfirmed), `busy`, `cooldown`, `succeeded` or `failed`.
Cooldown includes remaining minutes rounded up. If admission is not observed within
half a second, it reports `worker_started` (still starting, admission unconfirmed).
These are observations at submission time; use `hook-status` for updated evidence,
and do not infer that an old `started` snapshot proves a worker is still alive.
The retrieval hook waits for its own result independently of the user's turn
and memorization.
Background evolve processes mark their environment so they do not start another
memorization worker. Every submission can launch a lightweight worker. The worker
tries the whole-workspace lock once: if another run owns it, it records `busy` and
exits successfully without waiting. After acquiring the lock, it checks a persistent
30-minute cooldown measured from the last admitted run's start, records the new
start before prepare, and holds the lock through prepare → evolve → commit.
A run longer than 30 minutes still excludes every other worker. `cooldown` skips
also exit successfully. Both skips leave cursors and pending work untouched.

Every admitted run consumes cooldown, including failure, no new input, and a
successful no-op. A crash releases the OS lock and keeps its recorded start time;
retry requires a later submission after cooldown. At exactly 30 minutes a new
submission can run. For example: a 10:00 start skips a 10:10 submission; if the
next submission is at 11:00, processing starts at 11:00. No submission at 10:30
means no automatic run. Content added while busy or cooling down waits for a
later admitted submission, possibly indefinitely after the last message; there
is no 30-minute ingestion guarantee or deferred rerun.

Lock and cooldown are shared by background, diagnostic and direct `hook-run`
execution. The stable workspace defaults to `~/.memu/hosts/codex`; the cooldown
file is `.memorize_last_started.codex.json` there, alongside `.diagnostic.lock`.
The presence of the lock file alone does not mean a process owns the lock.
`install-prompt-hook --base-dir <path>` registers that same path in the callback;
use it with `hook-run --base-dir <path>` and `hook-status --base-dir <path>` too.
A backward wall-clock jump or invalid cooldown content emits a warning and allows
one new run that rewrites the timestamp. Other state I/O and lock errors fail
with diagnostics. Retrieval continues on every submission independently of this
lock and cooldown.

### 3.0 Register and trust the hooks

Run the CLI command; it merges both memU `UserPromptSubmit` handlers into
`~/.codex/hooks.json`, backs up the original once, asks Codex app-server to load
it, trusts Codex's returned fingerprint, and verifies `trustStatus`:

```powershell
memu-codex install-prompt-hook
```

If `codex` is not on PATH or the active Codex home differs from the default,
pass the actual paths:

```powershell
memu-codex install-prompt-hook --codex 'C:/path/to/codex.exe' --hooks-file 'C:/Users/<user>/.codex/hooks.json' --cwd 'C:/path/to/install'
```

The command reports success only after Codex confirms asynchronous retrieval
(`async: true`) and that both registered hooks are trusted. If Codex does not
confirm async support, update Codex and retry. Use this command for registration
and trust, and `hook-status --since` for runtime checks. If it fails, follow
**Execution permissions** and rerun after the relevant access issue is fixed.
Do not edit trust fingerprints manually.

### ✅ Verify Part 3

Require `install-prompt-hook` to confirm that both hooks are registered and trusted.
That completes this installation gate. After the next user message, runtime
execution can be checked once with:

```powershell
memu-codex hook-status --since <ISO-8601-time>
```

Successful retrieval context return or an empty result is valid. With asynchronous
retrieval, evidence may still be pending after the reply; a later `hook-status`
check can observe completion. `context_returned` means the hook emitted context,
not that the model has consumed it. Memorization appears as `started`, `succeeded`,
`busy` or `cooldown`. Missing evidence before the first subsequent message is
normal. Keep retrieved memory out of installation diagnostics; if the user asks
what was retrieved, answer from the actual context available for that message
without inventing results. All legacy cleanup belongs to M3 and is completed
during installation.

---

---

## Existing installations — migration

Use this branch when Codex already has a memU schedule, retrieve skill or hook. Keep the existing backend and progress; do not reinitialize a
store to repair trigger configuration. The new-install parts above describe the
replacement entries, while this section owns legacy discovery, handoff and cleanup.

### M1 — Identify the old entry points

Query Codex's native automations through its management tools. Candidate names
are {{all_task_names}}. Confirm that each matching task's prompt invokes Codex's
memU prepare / self-evolve / commit pipeline; a name alone does not establish
ownership. Use the confirmed IDs and current running states for M3. Leave
unrelated or ambiguous tasks untouched. If inventory is unavailable, report it
as unresolved. No matching task is normal; handle every confirmed match.

### M2 — Verify the replacement before removing anything

Complete Parts 1–3's backend verification, Submit hook registration and prompt-hook
registration/trust, reusing results already obtained in this run. Then handle
all legacy entries in M3 before announcing installation completion. Keep new
background workers from processing the workspace until the old tasks are idle.
Runtime verification follows the next user message and does not delay cleanup.

### M3 — Migrate and remove legacy entries


This is the single cleanup stage for old memU schedules, retrieval skills,
managed instruction pointers and other version-specific residue. Add future
legacy cleanup requirements here. Process both checklists before leaving this
stage. Use M1's ownership results without repeating discovery. Preserve
backend configuration, memories, session cursors and unrelated integrations.

#### Old scheduled tasks

Use M1's confirmed IDs. After M2 passes, pause each old automation through
Codex's management tool. For `update`, pass `kind: "cron"` and the full current
definition returned by the tool (name, prompt, rrule, projectId, model,
reasoningEffort, executionEnvironment, status); change only status to `PAUSED`.
Preserve the
prompt exactly. Verify the paused status; missing required arguments do not
mean the tool lacks update support.

Wait for any running old task and its descendants to finish naturally before
allowing the new background worker to process the same workspace. Prevent new memU
memorization launches during this handoff; if that cannot be done safely, stop before
changing registrations. Do not kill running tasks.

Once idle, delete the confirmed old automations by ID and query again to verify
removal. M2's verified registration is the replacement gate; do not wait for a
new background run before deleting old schedules. Preserve unrelated automations
and session history; use Codex's management tool rather than editing its database.

#### Old retrieve skill and AGENTS pointer

After Part 3 confirms the new hook is loaded and trusted, remove the old
retrieval entry in this installation turn, even if runtime verification awaits
the next user message. Confirm memU ownership of
`~/.codex/skills/memu-retrieve/SKILL.md` and the managed AGENTS pointer; stop if
ownership or user edits are ambiguous.

Review the targeted removal, then apply it:

```text
memu-codex remove-instruction --dry-run
memu-codex remove-instruction
```

Use this CLI to remove the managed block and owned skill, including when the
block says "do not edit". Respect explicit user instructions forbidding removal.
Verify both are gone and unrelated content remains. Preserve other skills,
AGENTS instructions and the distribution/install SKILL.md. Custom locations or
unmarked references require confirmed ownership and targeted cleanup.

#### Verify legacy cleanup

Check every M3 cleanup item together: confirmed old schedules are gone, the owned
retrieval skill and AGENTS pointer are gone, and unrelated entries survive.
Explicitly report each as removed or already absent. A running old task,
missing inventory, an ownership question or an unhandled legacy entry is a
cleanup blocker; identify it rather than postponing cleanup until a new hook
runs. Keep backend config, memory, session cursors and logs intact.

---

## Report the outcome to memU

memU is otherwise blind to whether any of this worked: an install that died in
Part 2 looks exactly like one that was never attempted. Report once when this
run succeeds or encounters an actual failure:

It is best-effort throughout and never part of the install — if the command
fails, ignore it, and if `memu-codex` is not on `PATH` (a Part 1 that never
finished), there is nothing to report with, which is fine.

**Every gate passed:**

```
memu-codex report install
```

The event's *existence* is the success signal: there is no failure flag, and
nothing leaves the machine here — it records locally and returns.

After registration and cleanup pass, run `report install` even if the first
user-triggered runtime check has not occurred. Give Part 2's activation message;
waiting for the next message is normal after successful installation.

**An installation step failed or a required prerequisite is unavailable** —
tell the user and report the actual failure:

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

Give one concise final report in a consistent language. Combine installation
success, the next-message invitation and background log location into that
report; do not append a second activation paragraph or repeat the same facts
in English and Chinese.

Report back to the user:

- remind the user they can switch back to their previous permission mode after
  installation;
- notify startup status and the exact local log path, or Part 2's activation
  message and resolved log directory when awaiting the next user turn;
  memorization continues in the background and its completion is not an
  installation gate;
- the selected mode and its cloud endpoint or local store/provider;
- the verified Submit memorization entry and the outcome of old-task migration;
- the retrieval entry retained or installed for this machine, and whether a fresh
  Codex session is needed to pick it up.

Record and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the backend configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
