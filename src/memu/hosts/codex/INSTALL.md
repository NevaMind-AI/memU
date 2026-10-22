# Install memU for Codex

<!-- memu-codex-record: notify-v2 -->
<!-- memu-codex-permissions: v7 -->

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

## Before installing — choose the guide language

Before stage 1, the Full access check, or any installation commands, use the
language explicitly selected for this installation. If none was selected, the
first response is a **language-selection turn only**. Use an available choice
tool with EN, ZH and a free-text Other answer. If unavailable or disallowed,
reproduce the following prompt exactly, without a preface:

```text
🌐 Choose your installation language / 请选择安装引导语言

1. EN — English
2. ZH — 中文
3. Other — enter your preferred language / 输入其他语言
```

**End the response immediately after the question and wait for the answer.**
Until the user chooses, do not check or discuss permissions, mention Full access,
print a numbered stage, run commands, read another guide, or explain later steps.
The language prompt is the entire response, not a summary of this document.
If Other has no language filled in, ask only which language and wait again.
Do not infer a selection from the initial request's language alone.
Use the selected language
for all progress, permission prompts, blockers and the final report, preserving
commands, paths and configuration keys. For Chinese guidance, name the setting
`Full access / 完全访问权限` and ask the user to reply `继续安装`. Use this prompt:

> 安装需要写入用户目录并配置 Codex 集成与后台任务，当前沙箱模式可能阻止这些操作。
> 请临时切换到 **Full access / 完全访问权限**，然后回复“继续安装”。
> 安装完成后可切回原权限模式。

Use `danger-full-access` to check effective permissions internally; the
user-facing setting name should match the selected language's UI label.
Reuse the choice from `SKILL.md` without
asking again. This introduction is outside the five numbered stages.

## Installation progress — five stages

Use the user's language and print each stage message once before its work.
If already printed while following `SKILL.md`, continue that stage rather than
restarting the counter. Use these messages instead of command-by-command
narration; explain a blocker in one short sentence with the required next action.

| Stage message | Work |
| --- | --- |
| 🔐 [1/5] Checking installation permissions | Full-access gate below |
| 📦 [2/5] Preparing memU and the memory backend | Part 1; reuse existing configuration |
| 🔔 [3/5] Setting up automatic memorization | Part 2 registration; old-schedule handoff if needed |
| 🧠 [4/5] Setting up memory retrieval | Part 3 registration and trust |
| 🚀 [5/5] Starting your first memorize task | One short turn for both hook checks; legacy instruction cleanup |

After successful installation checks, print `✅ memU installation complete`,
the background task status and exact log path, then the permission-mode reminder.
For a blocker or pending startup, name the stage and remaining action instead
of announcing completion. Background job processing does not add stages.

## Execution permissions — Full access before installation

Before package installation, `init`, setup or migration changes, inspect the
current session's actual sandbox mode. Continue only with `danger-full-access`.
Approval policy is separate: `approval_policy = never` does not establish Full
access. If sandbox mode is not provided, say that you cannot confirm it and ask
the user to check the setting.

Otherwise pause installation and tell the user:

> Installation needs to write to your user directory and configure Codex
> integrations and background execution. The sandbox may block these operations
> even after directory access is approved. Please temporarily switch to Full
> access, then reply "continue installation". You can switch back to your previous
> permission mode after installation.

Confirm the current session's effective mode after the user replies, then resume
from the pending step in this conversation. If it still reports restricted
permissions, report that the change has not taken effect and remain paused at
stage 1. Do not switch modes or change Windows ACLs yourself.
Normal OS permissions still apply in Full access; an access error must be
resolved before continuing. Do not rerun an unchanged failing command.


## Installation checks — keep the user-facing flow short

Reuse successful checks from this run: resolve executables once, run `doctor`
once after the final backend/package change, and use one short fresh Codex turn
for both hook checks. Only repeat a check when a relevant change invalidates it.
Record notify startup and its log path, then leave memorization running in the
background. Full memory evolution and cursor validation belong to development
acceptance, not the interactive installation.

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

### 1.1 Install

```
pip install --upgrade memu-cli
```

**`--upgrade` matters, and a bare install is not enough.** A machine that
already carries an older `memu-cli` keeps it otherwise, and this guide names
subcommands (`init`, `config`) that older builds answer with `invalid choice`.
If you meet that error anywhere below, you are on a stale build: upgrade, then
re-run the command that failed.

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
`PATH`. Fix that now rather than working around it — the notify worker in Part 2
and the hook in Part 3 both need a usable executable in a non-interactive
environment.

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

### ✅ Verify Part 2

Use the single short Codex turn in Part 3 to check both hooks. For notify, confirm
that a new log under `~/.memu/hosts/codex/log/hooks/notify/` records the worker
starting for that turn. Allow at most 15 seconds for startup; if it is not
observed, report startup as pending and provide the log directory.

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

### 3.0 Preflight — app-server access before hook edits

When using app-server for trust, first verify it can start against the real
Codex home. Resolve that home from the existing configuration/environment;
sandbox `USERPROFILE` or home lookup can differ from the signed-in user's.
If lookup fails, pass the confirmed home environment and `CODEX_HOME` to the
child process without changing which user's configuration is used.

Before launching, resolve the installed version's actual temporary-file and
SQLite runtime paths. On the verified Windows
CLI, `state_5.sqlite` and its `-wal` / `-shm` files live directly under
`~/.codex/`, not `~/.codex/sqlite/`. App-server needs writable state files,
parent access for creating companion files, and `~/.codex/tmp/`. Other versions may
use different names or additional runtime files. Do not hard-code this one
version's list as complete, move the database, delete locks or reset state.

Prefer a small subprocess script that keeps stdin open, reads JSON responses
with a bounded timeout and closes the child in `finally`; match the installed
Python or PowerShell version. This avoids a separate approval for every input
to an escalated terminal.
Start `codex app-server --stdio` and send this `initialize` request:

```json
{
  "id": 1,
  "method": "initialize",
  "params": {
    "clientInfo": {"name": "memu-install", "version": "1"},
    "capabilities": {"experimentalApi": true}
  }
}
```

Wait for its successful response, send `initialized`, then call `hooks/list`
with the installation directory in `cwds` and wait for its response. Empty hooks
are valid at this stage; startup failure,
RPC errors or hook-loading errors fail this gate. Do not pipe all requests and
immediately close stdin, or treat `codex --version` as this check.

If startup or access fails, follow **Execution permissions** above. An approved
request is not proof of effective access. Verify startup again only after a
relevant change, and do not edit the hook or trust state while this gate fails.
Once it passes, register the command below and use a live app-server connection
that reads the final definition for trust approval.

### 3.1 Register the command

Resolve the installed `memu-codex` executable to an absolute path. The hook must
use that executable followed by `prompt-hook`, so it does not depend on Codex's
background PATH. Use the host's command shell syntax: an executable path with
no spaces needs no quotes. For Windows PowerShell, a quoted executable must be
invoked with `&`, for example `& 'C:/Program Files/memu/memu-codex.exe' prompt-hook`.
A bare `"C:/path/memu-codex.exe" prompt-hook` is a PowerShell parse error: trust
can succeed while the process never starts and no memU log is created. For POSIX
shells, quote paths containing spaces using that shell's syntax. Windows JSON
paths can use forward slashes. Write `hooks.json` as UTF-8 without a BOM;
Windows PowerShell 5.1's `Set-Content -Encoding utf8` adds a BOM that Codex rejects.
Use a writer with explicit BOM-free UTF-8, then require `hooks/list` to load the
file without parse warnings.

Back up `~/.codex/hooks.json` locally, then merge a command hook under
`hooks.UserPromptSubmit`. Preserve every unrelated event, matcher and command;
if the exact memU entry is already present, reuse it instead of appending a
second entry. The following is the structure; replace the command with
the resolved path and the appropriate invocation syntax described above:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "<absolute-path-without-spaces>/memu-codex.exe prompt-hook",
            "timeout": 50,
            "additionalContextLimit": 0,
            "statusMessage": "Retrieving memU memory"
          }
        ]
      }
    ]
  }
}
```

The CLI currently implements `prompt-hook`; `install-hook` installs **notify
only**. Automatic retrieval-hook registration and trust management are not yet
integrated. Apply and verify these steps using the installed Codex version's
supported hook configuration and approval facilities. If those facilities are
unavailable, report Part 3 as incomplete; do not report a successful installation.

### 3.2 Add trust for the registered definition

After the command definition is final, approve that exact hook using Codex's
hook trust/approval mechanism. Registration alone does not establish trust.
On the currently verified Windows Codex version, persisted approval appears in
`~/.codex/config.toml` under `hooks.state`, keyed by the absolute hooks file path,
`user_prompt_submit`, matcher index and command index, with a `trusted_hash`.
Those indices must match the merged configuration; do not assume `0:0` when
other hooks already exist.

Preserve unrelated approvals. Do not copy a fingerprint from another machine,
path or hook definition, or invent a hash algorithm. If the command definition
changes during an upgrade, recheck its approval with the installed Codex version
before relying on it. An existing identical, trusted entry can be retained.

For the verified CLI 0.163.0, automation can use `codex app-server --stdio`:
initialize the JSON-RPC connection as in Part 3.0, then call `hooks/list` with the installation
working directory in `cwds`. Select the exact registered `userPromptSubmit`
entry by `sourcePath` and `command`; use its returned `key` and `currentHash`.
Parse these directly from the JSON response; do not retype a fingerprint from
wrapped terminal output, which can duplicate or truncate characters.
After reviewing that command, call `config/value/write` with
`keyPath = hooks.state.<TOML-quoted returned key>.trusted_hash`,
`value = <returned currentHash>` and `mergeStrategy = upsert`.
Call `hooks/list` again and require `trustStatus = trusted`. This uses Codex's
own fingerprint and config writer. Do not pass `--dangerously-bypass-hook-trust`
as a substitute for registration or verification.

### ✅ Verify Part 3

Read back the merged hook configuration and its corresponding trust state.
Confirm one intended memU command and an existing executable; retain unrelated
hooks and user configuration.

Use one fresh Codex turn with a fixed short reply to check hook execution;
reuse the same turn for Part 2. Inspect only the matching retrieval log's status
and exit code under `~/.memu/hosts/codex/log/hooks/retrieve/`. Successful context
return or an empty result is valid; do not inspect or display retrieved memory
as part of installation. An untrusted or unexecuted hook does not pass.

After retrieval and notify startup are confirmed, finish installation and
report the background log path. Legacy skill cleanup belongs to the migration
section and does not depend on the new memorize worker finishing.

---

---

## Existing installations — migration

Use this branch when Codex already has a memU schedule, retrieve skill, hook or
notify callback. Keep the existing backend and progress; do not reinitialize a
store to repair trigger configuration. The new-install parts above describe the
replacement entries, while this section owns backups, handoff and cleanup.

### M1 — Inventory and preserve the old entry points

Inspect both Windows Task Scheduler (all task folders) and Codex's own
scheduled-task surface when present. Candidate names are {{all_task_names}}.
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
5. Use Part 2's worker-startup check and share its log path. If no old schedules
   exist, proceed directly to Part 3 and M4. Do not wait for the new worker's
   jobs or commit. If old schedules exist, perform the production startup check
   only after their safe handoff below; do not launch competing workers.

### M3 — Complete the schedule switch

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

Once idle, enable/retain the memU notify callback and use the single short
Codex turn from Part 3 to confirm worker startup as described in Part 2. On a
startup error, follow Recovery and restore the old entry; do not delete its
registration. The new worker continues in the background.

Remove only the confirmed, now idle old registrations after this startup check passes. Re-list both scheduler
surfaces and verify that unrelated registrations survive. Keep the saved
definitions, wrappers, logs, backend config, memories and session cursors.
A repeated migration with no remaining old task is a no-op; it must preserve the
existing memU notify and retrieval hooks.

### Migration recovery

If a replacement gate fails, leave the old registration unchanged. If a problem
appears after disabling/removing it, first stop future memU notify launches while
preserving the user's other notifier, then wait for any worker to finish.
Restore the exact saved task path/ID, definition and original enabled state
through the same scheduler, using its supported import. S4U/password principals
may require credentials again; verify the restored registration and referenced
files before relying on it. Do not reset the backend or cursor to repair a trigger.

### M4 — Remove the old retrieve skill and its AGENTS pointer

First complete Part 3's prompt-hook registration, trust and real-turn verification.
Keep the old retrieval entry until the replacement works. Back up
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

This removes memU's marked AGENTS pointer first, then the owned `memu-retrieve/`
directory, including its `SKILL.md`. Preserve all unrelated skills and user
instructions. Do not delete `~/.codex/skills/`, another host's skill or memU's
distribution/install SKILL.md. A custom location or unmarked reference requires
explicit ownership confirmation and targeted cleanup; do not delete user text.

Use Part 3's single fresh-turn result for this gate; do not launch another
model turn or wait for the new memorize worker. Read back both locations: the
old owned skill and pointer must be gone and unrelated content intact. Reuse
the verified hook trust and notify-startup evidence from this installation.
Repeating cleanup with no old entry is a no-op. If retrieval must
be reverted, restore only the backed-up owned skill and its pointer, preserving
unrelated edits made since backup.

### ✅ Verify migration

Report verified notify and trusted prompt-hook entries, confirmed schedules
removed (or none found), old skill/pointer cleanup and local recovery location.
Leave migration pending while a gate, old scheduled agent or ownership question
remains unresolved. The new memorize worker may continue in the background.
Keep backend config, memory, session cursors and logs intact.

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
- notify startup status and the exact local log path; memorization continues in
  the background and its completion is not an installation gate;
- the selected mode and its cloud endpoint or local store/provider;
- the verified notify record entry and the outcome of old-task migration;
- the retrieval entry retained or installed for this machine, and whether a fresh
  Codex session is needed to pick it up.

Record (Part 2) and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the backend configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
