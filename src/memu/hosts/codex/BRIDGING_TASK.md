---
name: create-memu-bridging-task
description: Register an OS-scheduled Codex run that bridges recent Codex sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Codex)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Codex sessions into memU memory files, skills, and resource submissions.

Memory and skills are durable in both modes. In cloud mode, the current service
accepts workspace resources from this unchanged pipeline but does not persist or
retrieve them yet.

Your goal is to **register a recurring headless Codex run with the OS scheduler**.
Do not create a ChatGPT/Codex native scheduled task. You are not running the
pipeline now; you are registering the schedule that will run it later.

Part of the full setup in `INSTALL.md` (`memu-codex docs install`), but usable on
its own to add, migrate, or re-schedule the task on a machine where memU is
already installed.

## What the bridging task does (context)

Each run walks a fixed pipeline that bridges raw session history into memU:

1. **Prepare** — `memu-codex prepare` scans new turns under `~/.codex/sessions`,
   mirrors the current memU recall files to `~/.memu/hosts/codex/memory` and
   `~/.memu/hosts/codex/skill`, snapshots them by content hash, and writes
   numbered **job-instruction files** to `~/.memu/hosts/codex/jobs/` (`1.txt`,
   `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is
   an allowed, common outcome for any job.
3. **Commit** — `memu-codex commit` diffs the tracked directories against the
   step-1 snapshot and submits what the agent actually created or changed back
   to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the scheduled
run's prompt must instruct Codex to do it, not shell out to a pipeline script.

## Prerequisites

- **memU is installed and `memu-codex` is on `PATH`.** Verify with
  `memu-codex doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **The standalone `codex` CLI resolves and is already authenticated** for the
  same OS account the scheduler will use. Codex reads its profile authentication
  (normally `~/.codex/auth.json`); there is no separate Desktop-to-CLI token
  setup in this guide.
- The scheduled invocation deliberately uses
  `--dangerously-bypass-approvals-and-sandbox`. That removes **Codex's** approval
  prompts and sandbox for this controlled, fixed automation prompt. It does not
  grant administrator/root privileges or bypass the OS scheduler account,
  Windows S4U restrictions, cron's sparse environment, macOS TCC/Keychain,
  firewall/VPN/proxy/CA policy, enterprise policy, or Codex login. Never adapt
  this wrapper to run an untrusted or user-supplied prompt.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm before creating.

## Step 2 — Legacy native-task migration

> This compatibility section exists only for installs made by the older guide.
> It is deliberately self-contained so a future major release can remove it
> without changing the canonical OS-scheduler procedure below.

**Never install the OS task beside a native memU task.** ChatGPT Work and Codex
Desktop share the same native scheduled-task system, while `codex-cli` has no
native task-management interface. Use the Codex Desktop task-management surface
as the source of truth:

1. List every native scheduled task. Before changing anything, make a private
   local backup of each possible memU candidate's task id, name, schedule, full
   prompt, and updated time.
2. Classify by the full prompt, never by task name alone:
   - A task whose prompt contains exactly
     `MEMU_BRIDGING_TASK_ID=memu:bridging:codex:v1` is an explicitly owned memU
     task.
   - Without that marker, treat a task as a legacy memU candidate only when its
     prompt contains **all four** strings: `Run the memU bridging pipeline`,
     `memu-codex prepare`, `memu-codex commit`, and
     `~/.memu/hosts/codex/jobs`.
   - Leave every other task unchanged. Show every unmarked legacy candidate to
     the user and obtain explicit confirmation before deleting it.
3. Delete only approved candidates, by native task id, through the Desktop
   task-management surface. Never edit the scheduler's storage files directly.
4. List native tasks again. Continue only when no owned task and no approved
   legacy candidate remains. **If listing, deletion, classification, or verification fails, stop.**
   **Do not create the OS task.** Report the blocker so two schedulers can never
   process the same jobs concurrently.

This is migration, not uninstall. Keep the memU package, retrieval instruction,
`~/.memu/hosts/codex/`, session manifests, pending `jobs/`, memory/skill mirrors,
config, and memory store. The first OS run intentionally drains leftovers before
preparing new work.

## Step 3 — register the OS-scheduled run

**Never inline the pipeline prompt in a crontab or Task Scheduler command.** The
quoted prompt is over 1 KB: cron implementations can truncate long crontab lines,
and Task Scheduler re-parses action arguments. Both platforms therefore use the
same shape: **the prompt lives in a file; the scheduler starts a short wrapper.**

### macOS / Linux (cron by default)

1. Write the pipeline prompt to
   `~/.memu/hosts/codex/bridge-prompt.txt`, this content **verbatim** as one line:

   ```
   Run the memU bridging pipeline. Do the four steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. LEFTOVERS. If ~/.memu/hosts/codex/jobs/ already contains job files, they are unfinished work from an earlier run (a crash, or the install itself) — process them exactly as step 3 describes, then run:  memu-codex commit  — and only then continue.  2. PREPARE. Run this exact command with bash:  memu-codex prepare  — it regenerates ~/.memu/hosts/codex/jobs/. If the command exits non-zero, stop and report the error.  3. SELF-EVOLVE. List ~/.memu/hosts/codex/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 4. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  4. COMMIT. Run this exact command with bash:  memu-codex commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  ON FAILURE. If step 2 or step 4 exited non-zero, run this once before you stop:  memu-codex report error --stage remember --detail "<a full account of what went wrong>"  — that detail is all a memU engineer gets to work out what is broken on this machine, so be generous: which step, what you ran, what happened instead, what you already tried, and what you think the cause is. Write it as prose for a human, not as a transcript — do not paste the traceback or raw command output, which the CLI already reports on its own, and keep credentials, absolute paths, and memory or transcript text out of it. Ignore any failure of that command; it is never part of the run.  Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed.
   ```

2. Write `~/.memu/hosts/codex/bridge.sh` and `chmod +x` it:

   ```sh
   #!/bin/sh
   # memU bridging for Codex — invoked by cron.
   DIR="$HOME/.memu/hosts/codex"
   LOCK="$DIR/.bridge.lock"
   if ! mkdir "$LOCK" 2>/dev/null; then
     if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then
       rmdir "$LOCK" 2>/dev/null
       mkdir "$LOCK" 2>/dev/null || exit 0
     else
       echo "$(date '+%F %T') skipped: another bridging run is in progress" >> "$DIR/bridge.log"
       exit 0
     fi
   fi
   trap 'rmdir "$LOCK" 2>/dev/null' EXIT INT TERM
   export MEMU_BRIDGING_RUN=1
   codex exec \
     --dangerously-bypass-approvals-and-sandbox \
     --skip-git-repo-check \
     --cd "$DIR" \
     "$(cat "$DIR/bridge-prompt.txt")" \
     >> "$DIR/bridge.log" 2>&1
   status=$?
   exit "$status"
   ```

   Do **not** add `--ephemeral`: the saved rollout is the diagnostic record for a
   failed unattended run and keeps scheduled behavior consistent with ordinary
   Codex sessions.

3. Cron starts with a sparse environment. Derive and put this `PATH` line above
   the entry, using the actual resolved command locations at registration time:

   ```
   PATH=$(dirname "$(command -v memu-codex)"):$(dirname "$(command -v codex)"):/usr/local/bin:/usr/bin:/bin
   ```

   Then add the one short entry (or an equivalent launchd job if the user chose
   launchd explicitly):

   ```
   0 * * * * $HOME/.memu/hosts/codex/bridge.sh
   ```

### Windows (Task Scheduler)

Do not hand-write a `schtasks` entry. After the legacy gate has passed, use the
shared deterministic helper:

```
memu-codex schedule install     # register the hourly OS task
memu-codex schedule verify      # prove a resolvable Codex CLI
memu-codex schedule status      # last run / next run
memu-codex schedule uninstall   # remove it
```

`install` writes `bridge-prompt.txt` and a PowerShell wrapper under
`~/.memu/hosts/codex`, resolves `codex` to an absolute path, and registers
`\memU\memu-bridging-codex` under an S4U principal — hidden, limited rather than
administrator, runnable while logged out, and able to catch up a run missed
while the machine was off. `--interval <minutes>` changes the cadence (default
60). The wrapper restores `PATH`, uses the Codex flags documented above, appends
stdout/stderr to `bridge.log`, and propagates the CLI exit code.

## Step 4 — verify and report

**Your interactive shell proves less than the scheduler's actual account and
environment.** Verify the registered OS task rather than only running the wrapper
in the current terminal:

- Unix: confirm the `PATH` header and one short wrapper entry in `crontab -l`
  (and no native memU task). Trigger one run through cron, or faithfully reproduce
  its sparse environment, then check that `bridge.log` grew and the session
  manifest / `jobs/` timestamps moved.
- Windows: run `memu-codex schedule verify` and `memu-codex schedule status`, then
  trigger the canonical Task Scheduler task once. Check `LastTaskResult`, log
  growth, and filesystem traces under `~/.memu/hosts/codex/`.
- A successful interactive `codex exec` does not establish S4U/cron parity. If a
  scheduled run fails, compare its account, `HOME`, `PATH`, proxy/CA environment,
  Codex path, and login state with the intended user environment.

Report back: where the task was registered, its canonical identity and schedule
in words, whether legacy native migration was needed, and the evidence from the
first scheduled run. Mention that the first run only has new work once there are
new Codex sessions, apart from deliberately retained leftovers.

## Notes

- **Leftovers run before prepare.** Existing job files are unfinished work. Since
  `prepare` regenerates the directory after the cursor has advanced, draining
  leftovers first prevents silent loss.
- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/hosts/codex/.session_manifest.codex.json` and processes only unseen
  turns.
- **Single instance is load-bearing.** Cron uses the wrapper lock; Windows uses
  Task Scheduler's `IgnoreNew`. Concurrent runs would race on `jobs/` and commit.
- **Session self-skip is separate work.** This migration does not declare a Codex
  session-id environment variable or teach memU to exclude the scheduled
  rollout. Do not claim that native → OS migration fixes self-ingestion.
