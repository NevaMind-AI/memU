# Install memU for Codex

<!-- memu-codex-record: notify-v2 -->
<!-- memu-codex-permissions: v20 -->

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
| 🔔 [3/5] Setting up automatic memorization | Part 2 registration; old-schedule handoff if needed |
| 🧠 [4/5] Setting up memory retrieval | Part 3 registration and trust |
| 🚀 [5/5] Starting your first memorize task | One short turn for both hook checks; legacy instruction cleanup |

After successful installation checks, print `✅ memU installation complete`,
the background task status and exact log path, then the permission-mode reminder.
For a blocker, name the stage and remaining action. When registration and trust
succeeded and only the next user turn is needed, use the activation message in
Part 2 instead. Background job processing does not add stages.

## Execution permissions — Full access before installation

Before package installation, `init`, setup or migration changes, inspect the
current session's actual sandbox mode. Continue only with `danger-full-access`.
Approval policy is separate: `approval_policy = never` does not establish Full
access. If sandbox mode is not provided, say that you cannot confirm it and ask
the user to check the setting.

If the session is restricted or its mode is unknown, pause at stage 1 and show
**both** options below so the user can choose:

- **Codex Desktop:** ask the user to switch to **Full access / 完全访问权限**
  and reply "continue installation" here. Recheck the effective mode before
  resuming; remain paused if the change has not taken effect.
- **Codex CLI:** ask the user to exit and start a new session from the same
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


## Installation checks — keep the user-facing flow short

Reuse successful checks from this run: resolve executables once, run `doctor`
once after the final backend/package change, and only test changed integrations.
For an unchanged hook command with current trust and matching successful local
logs, reuse that evidence instead of starting another model turn. Otherwise use
one short fresh Codex turn for both hooks. Only repeat a check when a relevant
change invalidates it.

Batch independent read-only checks into one call and return a concise summary,
not whole configurations, guides or logs. Read this guide once. Resolve the
Codex executable before registering notify so `install-hook` runs once. Use one
app-server connection for preflight, registration/trust readback; match RPC
responses by id while skipping notifications. Check both hook logs in one call.
Print stage headings before their work, never together retrospectively.

If Part 3's existing hook is already loaded and trusted, its `hooks/list`
response satisfies preflight and trust readback; do not open another connection
or rewrite identical trust. Use `hook-status --since` for runtime log readback. A registration already completed in this run also
satisfies M2; do not execute the same install command again for migration.

If Windows blocks package replacement because a worker is using that environment,
report the installation blocker and resume after it exits; do not spend the
interactive installation inventing alternate tool directories or rebinding shims.

Record notify startup and its log path, then leave memorization running in the
background. Full memory evolution and cursor validation belong to development
acceptance, not the interactive installation. Finish with at most four short
lines: result/backend, migration status, exact background log path, and the
permission-mode reminder. Do not recap commands or diagnostics after success.

## Choose the installation path

**New installation:** follow Parts 1–3 below.
**Existing installation:** start with **Existing installations — migration**
later in this same guide. It references the setup parts for the new entries and
owns old schedule/skill cleanup. Read this guide once; no additional docs command
is needed.

New installation has three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Register and verify notify** — turn recent
   Codex sessions into durable memory (the *record* seam).
3. **Register and trust `UserPromptSubmit`** — retrieve memory before each
   user turn (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

## Notify record trigger (Codex)

The record trigger is Codex notify: prepare → headless `codex exec` → commit.
Follow Part 2 after the backend gate passes. Existing installations use the
migration section for safe handoff.

---

## Part 1 — Install memU

memU is distributed as a **pip package**. There is no npm package — do not look
for one; a Python runtime is required regardless, because the bridging task runs
Python.

### 1.1 Reuse the installed package

If you followed `SKILL.md`, package installation and executable selection are
already complete. Reuse that installation, source and executable path; do not
install again or repeat successful executable checks.

If you opened this guide directly and have not installed or updated the package,
use the user's requested package manager and source. The default is:

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

## Part 2 — Register and verify notify

The *record* seam runs after a Codex turn: prepare → headless `codex exec` →
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
`memu-codex install-hook`; a persistent PATH change does not refresh an already
running Desktop or its shells. Read the registered `--agent` back and require an
absolute path to the verified executable. Restart Desktop or open a fresh session
when necessary, then check the callback again.

Keep the existing Codex home, model/provider and authentication configuration.
Desktop and CLI normally share that configuration; reuse it before asking for
new credentials. A successful `--version` proves startup, while the real record
check below proves the configured execution path. If an existing CLI resolves
but cannot start, report and repair that failure before registration.

### 2.1 Register the callback

After the CLI probe and Part 1's backend gate pass, run:

```text
memu-codex install-hook
```

Read the configuration back and verify callback and agent executable paths exist.
Repeating an identical installation is a no-op. The installer replaces any
existing notify, including Desktop's `turn-ended` command, without a backup.
Other Codex settings are preserved. For old memU schedules or retrieval entries,
follow **Existing installations — migration** below.

### Runtime check — one CLI call

Before the short verification turn, record its start time (PowerShell:
`$since = [DateTimeOffset]::Now.ToUnixTimeSeconds()`). After the turn, run:

```text
memu-codex hook-status --since <start-time>
```

The command returns JSON with `retrieve.status`, `retrieve.exit_code`,
`notify.status` and each log path. Exit 0 means retrieval succeeded (context or
empty result) and notify startup was observed; exit 1 means retrieval failed;
exit 2 means evidence is pending. `notify.status = started` proves startup only,
not worker completion. Use this output directly instead of writing log parsers,
reading source code or enumerating processes. It does not wait or retrieve memory.
The time filter excludes logs started before the check; avoid concurrent test
turns, as the two newest logs are not correlated by session ID.

### ✅ Verify Part 2

Use matching startup evidence for an unchanged callback, or the single short
Codex turn in Part 3 when runtime testing is needed. For notify, confirm
that a new log under `~/.memu/hosts/codex/log/hooks/notify/` records the worker
starting for that turn. Allow at most 15 seconds for startup; if it is not
observed because no subsequent user turn has occurred, tell the user:

> Send one more message here to start your first memorize task. Memorization
> runs in the background and processes only new conversation content since the
> previous run. You can follow its logs in
> `~/.memu/hosts/codex/log/hooks/notify/`.

Resolve that directory to the user's actual local path. Explain that runtime
verification and any remaining schedule cleanup will follow their next message.
Complete M3's legacy-entry cleanup before asking for that message, except any
schedule removal that still requires a safe runtime handoff.
Continue in this conversation; a new session is unnecessary unless Codex reports
that the changed configuration requires one. If a verification turn already ran
without startup evidence, report the missing evidence or concrete error instead.

Once startup is observed, continue installation immediately. Do not wait for
memorization jobs, commit, cursor updates or worker completion, and do not tail
logs or poll the worker afterward. Tell the user their first memorize task has
started in the background and provide the exact local log path so they can
follow progress. A log containing an immediate startup error does not pass.
If the log already shows a successful no-op, report that result instead of
claiming memories were created. Keep raw logs local.

---

## Part 3 — Register and trust the UserPromptSubmit retrieval hook

This part owns the *inject* seam: Codex runs `memu-codex prompt-hook` when the
user submits a prompt. The command reads the hook's stdin JSON, passes the
original prompt to shared retrieval, and returns
`hookSpecificOutput.additionalContext` before the model answers.

### 3.0 Register and trust the hook

Run the CLI command; it merges the memU `UserPromptSubmit` hook into
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

The command reports success only after Codex confirms the exact registered hook
is trusted. If it fails, follow **Execution permissions** and rerun after the
relevant access issue is fixed. Do not edit trust fingerprints manually.

### ✅ Verify Part 3

Use matching successful local logs when the registered hook command is unchanged
and current trust is confirmed. Otherwise, use one fresh Codex turn to exercise
both hooks. If this session cannot initiate that turn, give Part 2's activation
message and resume verification after the user's next message. Then check once:

```powershell
memu-codex hook-status --since <ISO-8601-time>
```

Successful retrieval context return or an empty result is valid; notify must
show `started`. Do not inspect or display retrieved memory. An untrusted or
unexecuted hook does not pass.


After retrieval and notify startup are confirmed, finish runtime verification
and report the background log path. All legacy cleanup belongs to M3; its
retrieval cleanup follows registration and trust without waiting for runtime
verification or the new memorize worker.

---

---

## Existing installations — migration

Use this branch when Codex already has a memU schedule, retrieve skill, hook or
notify callback. Keep the existing backend and progress; do not reinitialize a
store to repair trigger configuration. The new-install parts above describe the
replacement entries, while this section owns backups, handoff and cleanup.

### M1 — Inventory and preserve the old entry points

Inspect both Windows Task Scheduler (all task folders) and Codex's own
scheduled-task surface when present. Windows Task Scheduler cannot establish
that Codex native automations are absent; query those through the available
Codex automation tools. If that inventory is unavailable, report it as unresolved.
Candidate names are {{all_task_names}}.
A name is only a search hint: confirm that the action, wrapper or prompt invokes
**Codex's** memU prepare / self-evolve / commit pipeline. Generic historical
names may belong to another host. Leave unrelated or ambiguous tasks untouched
and report them for review. Do not use another host's `schedule uninstall`.

Before changing a confirmed registration, save its exact task path/ID,
action and arguments or full prompt, working directory, principal, triggers,
enabled state and current running state locally. Export Windows task XML and
keep referenced wrapper/prompt files; use the native surface's supported export
for native tasks. If a restorable definition cannot be saved, stop migration.
Backups may contain private content and must stay local.

No matching task is a normal installation. Multiple confirmed registrations
must each be recorded; do not assume a single task or the `\\memU\\` folder.

### M2 — Verify the replacement before removing anything

1. Complete Part 2.0's CLI probe, installing the native CLI only if missing.
   A version check proves startup only, not authentication or model execution.
2. Keep the configured backend and pass `memu-codex doctor` from Part 1.
3. Run `memu-codex install-hook`, replacing any existing notify without a backup.
   Read the configuration back and verify the callback and agent paths exist.
   Repeating an identical installation is a no-op.
4. Verify the registered command is memU's callback and unrelated Codex settings
   are preserved.
5. Complete Part 3's prompt-hook registration and trust verification.
6. Enter M3 once to handle all legacy entries. If old schedules exist, perform
   the production startup check only after their safe handoff in M3; do not
   launch competing workers. Runtime verification may follow the next user
   message, but do not wait for the worker's jobs or commit.

### M3 — Migrate and remove legacy entries

This is the single cleanup stage for old memU schedules, retrieval skills,
managed instruction pointers and other version-specific residue. Add future
legacy cleanup requirements here. Process both checklists before leaving this
stage; a deferred schedule handoff does not defer safe retrieval cleanup.
Use M1's ownership results and backups without repeating discovery. Preserve
backend configuration, memories, session cursors and unrelated integrations.

#### Old scheduled tasks

Handle each scheduler independently:

- **Windows Task Scheduler:** disable the confirmed task by its exact task path
  and name, then unregister it after the handoff below.
- **Codex native automations:** use the Codex automation management tool with
  the confirmed automation ID. For `update`, include `kind: "cron"` and the
  complete saved definition (name, prompt, rrule, projectId, model,
  reasoningEffort, executionEnvironment, status); change only status to
  `PAUSED`. Verify by viewing it. After the handoff succeeds, call `delete` with
  the ID and verify the automation is gone. Do not infer that pause/delete is
  unavailable from a rejected update with missing required fields; do not
  reconstruct or shorten the saved prompt.
  Do not delete session history or edit the application database as a substitute.

Only after the replacement gates pass, disable future triggers on each confirmed
old registration through its original scheduler. Recheck its running state.
Deleting a registration does **not** terminate an already running agent; do not
kill it. Wait for the run and its descendants to finish naturally before allowing
notify to prepare the same working tree or cleaning any files. Old scheduled
agents do not necessarily acquire notify's workspace lock. If safe handoff cannot
be established, retain the saved disabled registration and report migration as
pending; do not claim completion. During this wait, prevent new memU notify
launches while retaining the user's other notifier; if that cannot be done
safely, stop before changing the old registrations.

Once idle, enable/retain the memU notify callback and reuse matching startup
evidence or the single short Codex turn from Part 3, as described in Part 2. On a
startup error, follow Recovery and restore the old entry; do not delete its
registration. The new worker continues in the background.

Remove only the confirmed, now idle old registrations after this startup check passes. Re-list both scheduler
surfaces and verify that unrelated registrations survive. Keep the saved
definitions, wrappers, logs, backend config, memories and session cursors.
A repeated migration with no remaining old task is a no-op; it must preserve the
existing memU notify and retrieval hooks.

#### Old retrieve skill and AGENTS pointer

First complete Part 3's prompt-hook registration and trust verification.
After Codex confirms the replacement is loaded and trusted, clean up the old
retrieval entry in this installation turn, including when runtime verification
awaits the user's next message. This prevents the old skill and AGENTS pointer
from requesting a second retrieval on that message. Back up
`~/.codex/skills/memu-retrieve/` and `~/.codex/AGENTS.md` locally.
Inspect `~/.codex/skills/memu-retrieve/SKILL.md` and the AGENTS pointer to confirm
memU ownership; the removal command treats SKILL.md in that named directory as
its ownership marker. Stop if ownership is ambiguous or user edits need review.

Preview and review the targeted removal:

```text
memu-codex remove-instruction --dry-run
```

Then apply:

```text
memu-codex remove-instruction
```

The managed block's "do not edit" warning requires this CLI writer; it is not a
reason to retain the obsolete entry once the replacement is registered and
trusted. If an actual
user instruction forbids removal, report migration as partial.

This removes memU's marked AGENTS pointer first, then the owned `memu-retrieve/`
directory, including its `SKILL.md`. Preserve all unrelated skills and user
instructions. Do not delete `~/.codex/skills/`, another host's skill or memU's
distribution/install SKILL.md. A custom location or unmarked reference requires
explicit ownership confirmation and targeted cleanup; do not delete user text.

Use Part 3's registration and trust result for this gate; do not launch another
model turn or wait for the new memorize worker. Read back both locations: the
old owned skill and pointer must be gone and unrelated content intact.
Runtime verification may follow on the next user message; it does not defer
this cleanup. Repeating cleanup with no old entry is a no-op. Use Cleanup
recovery below if runtime verification fails.

#### Verify legacy cleanup

Check every M3 cleanup item together: confirmed old schedules are removed or
explicitly pending a safe handoff, the owned retrieval skill and AGENTS pointer
are gone, and unrelated entries survive. Record the recovery location. Missing
inventory, an ownership question or an unhandled legacy entry leaves migration
partial. Keep backend config, memory, session cursors and logs intact.

#### Cleanup recovery

If a replacement gate fails, leave the old registration unchanged. If a problem
appears after disabling/removing it, first stop future memU notify launches while
preserving the user's other notifier, then wait for any worker to finish.
Restore the exact saved task path/ID, definition and original enabled state
through the same scheduler, using its supported import. S4U/password principals
may require credentials again; verify the restored registration and referenced
files before relying on it. For retrieval failures, restore only the backed-up
owned skill and AGENTS pointer, preserving unrelated edits made since backup.
Do not reset the backend or cursor to repair a trigger.

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

- remind the user they can switch back to their previous permission mode after
  installation;
- notify startup status and the exact local log path, or Part 2's activation
  message and resolved log directory when awaiting the next user turn;
  memorization continues in the background and its completion is not an
  installation gate;
- the selected mode and its cloud endpoint or local store/provider;
- the verified notify record entry and the outcome of old-task migration;
- the retrieval entry retained or installed for this machine, and whether a fresh
  Codex session is needed to pick it up.

Record (Part 2) and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the backend configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
