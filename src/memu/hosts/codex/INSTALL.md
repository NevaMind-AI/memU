# Install memU for Codex

<!-- memu-codex-record: notify-v1 -->

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

Installing memU on Codex is three parts:

1. **Install memU** — a Python package and the memory backend it uses.
2. **Verify the notify record trigger and migrate old schedules** — turn recent
   Codex sessions into durable memory (the *record* seam).
3. **Register and trust `UserPromptSubmit`** — retrieve memory before each
   user turn (the *inject* seam).

Parts 2 and 3 must share one configured mode. In local mode they must also share
one store and embedding space, or retrieval silently returns nothing. Part 1 is
what makes them agree.

## Notify record trigger (Codex)

The record trigger is Codex notify: prepare → headless `codex exec` → commit.
Follow Part 2 after the backend gate passes. Existing schedules stay available
until the replacement has been verified.

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

## Part 2 — Verify notify and migrate old record schedules

The *record* seam runs after a Codex turn. In cloud mode, workspace resources
are submitted but are not currently persisted. Complete notify registration
and historical schedule migration here.

### 2.1 Inventory and preserve the old entry points

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

### 2.2 Verify the replacement before removing anything

1. Resolve the standalone `codex` CLI and run `codex --version`. A version check
   proves startup only; it does not prove authentication or model execution.
2. Keep the configured backend and pass `memu-codex doctor` from Part 1.
3. If Codex has no notify command, run `memu-codex install-hook`. Read the
   configuration back and verify the executable and agent paths exist.
   Repeating an identical installation is a no-op.
4. If notify already exists, inspect it first. The current installer refuses to
   overwrite a different command, including a Desktop `turn-ended
   --previous-notify` wrapper. Preserve that wrapper and its existing forwarding
   chain. An already verified memU callback can be retained; if the replacement
   cannot be installed or verified, stop here with every old registration intact.
5. Check existing callback and worker evidence in
   `~/.memu/hosts/codex/log/hooks/notify/`, or validate the replacement in an
   isolated environment. Confirm prepare and commit/no-op results and cursor
   behavior; `codex --version` alone is insufficient. Keep raw logs local.
   Do not start a production smoke test while old schedules can launch into the
   same working tree; perform the final production check during the handoff below.

### 2.3 Complete the switch

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

Once idle, enable/retain the verified memU notify callback and use a real Codex
turn to check prepare → agent → commit/no-op in the production log. On failure,
follow Recovery and restore the old entry; do not delete its registration.

Remove only the confirmed, now idle registrations after this final check passes. Re-list both scheduler
surfaces and verify that unrelated registrations survive. Keep the saved
definitions, wrappers, logs, backend config, memories and session cursors.
A repeated migration with no remaining old task is a no-op; it must preserve the
existing notify chain and retrieval hooks.

### Recovery

If a replacement gate fails, leave the old registration unchanged. If a problem
appears after disabling/removing it, first stop future memU notify launches while
preserving the user's other notifier, then wait for any worker to finish.
Restore the exact saved task path/ID, definition and original enabled state
through the same scheduler, using its supported import. S4U/password principals
may require credentials again; verify the restored registration and referenced
files before relying on it. Do not reset the backend or cursor to repair a trigger.

### ✅ Verify Part 2

Report which notify chain was verified, which confirmed registrations were
removed (or that none existed), where local recovery definitions were saved,
and whether a running old agent still needs to finish. Installation or migration
is incomplete while a gate or safe handoff remains unresolved.

---

## Part 3 — Register and trust the UserPromptSubmit retrieval hook

This part owns the *inject* seam: Codex runs `memu-codex prompt-hook` when the
user submits a prompt. The command reads the hook's stdin JSON, passes the
original prompt to shared retrieval, and returns
`hookSpecificOutput.additionalContext` before the model answers.

### 3.1 Register the command

Resolve the installed `memu-codex` executable to an absolute path. The hook must
use that executable followed by `prompt-hook`, so it does not depend on Codex's
background PATH. Quote the executable path if it contains spaces. Windows JSON
paths can use forward slashes.

Back up `~/.codex/hooks.json` locally, then merge a command hook under
`hooks.UserPromptSubmit`. Preserve every unrelated event, matcher and command;
if the exact memU entry is already present, reuse it instead of appending a
second entry. The following is the structure, with the executable placeholder
replaced by the resolved path:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"<absolute path to memu-codex executable>\" prompt-hook",
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
initialize the JSON-RPC connection, then call `hooks/list` with the installation
working directory in `cwds`. Select the exact registered `userPromptSubmit`
entry by `sourcePath` and `command`; use its returned `key` and `currentHash`.
After reviewing that command, call `config/value/write` with
`keyPath = hooks.state.<TOML-quoted returned key>.trusted_hash`,
`value = <returned currentHash>` and `mergeStrategy = upsert`.
Call `hooks/list` again and require `trustStatus = trusted`. This uses Codex's
own fingerprint and config writer. Do not pass `--dangerously-bypass-hook-trust`
as a substitute for registration or verification.

### 3.3 Migrate the old retrieval instruction

Once the prompt hook is registered, trusted and verified below, remove the
previous memU retrieval skill and its AGENTS pointer, if present:

```
memu-codex remove-instruction
```

This removes memU's marked instruction and owned `memu-retrieve` skill while
preserving other instructions and skills. Keep the old entry until the new hook
has passed verification. A machine already using the trusted prompt hook needs
no new skill or AGENTS pointer.

### ✅ Verify Part 3

Read back the merged hook configuration and its corresponding trust state.
Confirm one intended memU command and an existing executable; retain unrelated
hooks, notify forwarding and user configuration.

In a fresh Codex session, submit a normal prompt and confirm that
`UserPromptSubmit` completes before the answer. Inspect the matching local log
under `~/.memu/hosts/codex/log/hooks/retrieve/` for hook status and the actual
`additionalContext` returned. Empty retrieval can be valid; an untrusted or
unexecuted hook does not pass. A direct `memu-codex retrieve` or `doctor` check
alone does not verify hook execution or trust. Keep prompts and retrieved memory
local.

Confirm the old memU skill and instruction pointer are gone after migration,
and that the notify chain from Part 2 still works. Use a fresh session after
changing hook definitions or global instructions.

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
- the verified notify record entry and the outcome of old-task migration;
- the retrieval entry retained or installed for this machine, and whether a fresh
  Codex session is needed to pick it up.

Record (Part 2) and inject (Part 3) both read `~/.memu/config.env`, so they
provably share the backend configured in Part 1 — what the task learns tonight
is what retrieval finds tomorrow.
