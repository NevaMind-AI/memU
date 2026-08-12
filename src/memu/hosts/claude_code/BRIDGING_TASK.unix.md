---
name: create-memu-bridging-task
description: Register a scheduled job that bridges recent Claude Code sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Claude Code)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Claude Code sessions into memU memory files, skills, and resource
submissions.

Memory and skills are durable in both modes. In cloud mode, the current service
accepts workspace resources from this unchanged pipeline but does not persist or
retrieve them yet.

Your goal is to **register a recurring headless Claude Code run** whose prompt is
the three-step pipeline below. You are not running the pipeline now; you are
registering the schedule that will run it later.

Part of the full setup in `INSTALL.md` (`memu-claude-code docs install`), but
usable on its own.

## What the bridging task does (context)

1. **Prepare** — `memu-claude-code prepare` scans new turns under
   `~/.claude/projects` (one JSONL file per session, one directory per project),
   mirrors the current memU recall files to `~/.memu/hosts/claude-code/memory`
   and `~/.memu/hosts/claude-code/skill`, snapshots them by content hash, and
   writes numbered **job-instruction files** to
   `~/.memu/hosts/claude-code/jobs/` (`1.txt`, `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is an
   allowed, common outcome for any job.
3. **Commit** — `memu-claude-code commit` diffs the tracked directories against
   the step-1 snapshot and submits what the agent actually created or changed
   back to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the scheduled
run's prompt must instruct the agent to do it, not shell out to a script.

## Prerequisites

- **memU is installed and `memu-claude-code` is on `PATH`.** Verify with
  `memu-claude-code doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **A standalone, headless-authenticated `claude` is on `PATH`.** The Desktop
  app cannot serve a scheduled run — its binary is off-`PATH` and its login is
  invisible to the CLI (memU#538). `INSTALL.md` Part 2.0 is the install +
  bare-environment verify procedure.
- **A headless run can execute the pipeline.** The scheduled run invokes
  `claude -p` non-interactively, so the commands and paths the pipeline touches
  must be pre-authorized in `~/.claude/settings.json` permissions with exactly
  these two rules: `Bash(memu-claude-code *)` and `Edit(~/.memu/**)`. The file
  rule must be `Edit(...)` — a `Write(~/.memu/**)` rule is silently ignored
  (the CLI itself warns that only `Edit` rules cover the file-editing tools;
  field data: an install shipped the `Write` form and every run carried the
  warning). Do **not** reach for a blanket permission-skip flag; the pipeline
  needs exactly those two things.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm before creating.

## Step 2 — register the scheduled run

**Never inline the pipeline prompt in the crontab entry.** The quoted prompt is
~1.2 KB, and cron truncates a crontab line at roughly 1 KB before handing it to
`/bin/sh` — the shell receives a command cut off mid-quote and every tick dies
instantly with `unexpected EOF while looking for matching "'"`, mailed to
`/var/mail/$USER` and visible nowhere else; `claude` never starts. Field data:
two hosts' inlined entries on one macOS machine failed exactly this way on every
tick, while the short script-invoking entry beside them kept working. This is
the Unix sibling of the Windows `schtasks /TR` limit (memU#539), and the fix is
the same shape: **the prompt lives in a file; the crontab line stays short.**

1. Write the pipeline prompt to
   `~/.memu/hosts/claude-code/bridge-prompt.txt`, this content **verbatim**
   as a single line:

   ```
   Run the memU bridging pipeline. Do the four steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. LEFTOVERS. If ~/.memu/hosts/claude-code/jobs/ already contains job files, they are unfinished work from an earlier run (a crash, or the install itself) — process them exactly as step 3 describes, then run:  memu-claude-code commit  — and only then continue.  2. PREPARE. Run this exact command with bash:  memu-claude-code prepare  — it regenerates ~/.memu/hosts/claude-code/jobs/. If the command exits non-zero, stop and report the error.  3. SELF-EVOLVE. List ~/.memu/hosts/claude-code/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 4. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  4. COMMIT. Run this exact command with bash:  memu-claude-code commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  ON FAILURE. If step 2 or step 4 exited non-zero, run this once before you stop:  memu-claude-code report error --stage remember --detail "<a full account of what went wrong>"  — that detail is all a memU engineer gets to work out what is broken on this machine, so be generous: which step, what you ran, what happened instead, what you already tried, and what you think the cause is. Write it as prose for a human, not as a transcript — do not paste the traceback or raw command output, which the CLI already reports on its own, and keep credentials, absolute paths, and memory or transcript text out of it. Ignore any failure of that command; it is never part of the run.  Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed.
   ```

2. Write `~/.memu/hosts/claude-code/bridge.sh` and `chmod +x` it:

   ```sh
   #!/bin/sh
   # memU bridging for Claude Code — invoked by cron.
   # The pipeline prompt lives in bridge-prompt.txt because cron truncates
   # crontab lines around 1 KB (see BRIDGING_TASK.unix.md).
   DIR="$HOME/.memu/hosts/claude-code"
   # Single-instance lock: an hourly tick can fire while a long backlog run is
   # still going; a second run would race it on jobs/ and double-commit.
   # mkdir is atomic; a stale lock older than 3h is reclaimed. Tradeoff: a
   # legitimate run longer than 3h loses its lock to the next tick and can
   # double-run — accepted deliberately, because the alternative (no reclaim)
   # lets one crashed run wedge the schedule forever. Do not "fix" one side
   # without weighing the other.
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
   # Marks this as the scheduled run, so `prepare` skips its own session instead
   # of mining memU's own bookkeeping every hour. Without it cron looks like a
   # person running prepare by hand (cron's cwd is $HOME, not $DIR), and the run
   # keeps feeding on itself.
   export MEMU_BRIDGING_RUN=1
   claude -p "$(cat "$DIR/bridge-prompt.txt")" >> "$DIR/bridge.log" 2>&1
   ```

**The crontab's first line is a `PATH`.** cron runs with a bare
`/usr/bin:/bin`; the binaries the pipeline needs (pipx and npm installs land in
`~/.local/bin` and `/opt/homebrew/bin`) are not there, and the run dies on
`command not found` before the pipeline starts. Derive it at registration time
and write it **above** the entry:

```
PATH=$(dirname "$(command -v memu-claude-code)"):$(dirname "$(command -v claude)"):/usr/local/bin:/usr/bin:/bin
```

The machine-specific fact lives in the crontab, where machine facts belong —
the pipeline prompt itself stays verbatim in its file.

Then the cron entry — the default, macOS included (use launchd only if the user
explicitly asks for it) — is one short line (cron does not expand `~` in the
command field, but it does run the line through `/bin/sh`, so `$HOME` works; a
literal absolute path is equally fine):

```
0 * * * * $HOME/.memu/hosts/claude-code/bridge.sh
```

The prompt block is fixed; only the cron expression is the user's choice.
Nothing machine-specific leaks into the prompt — the pipeline is invoked
through `PATH` commands. As a side benefit the run's output now lands in
`~/.memu/hosts/claude-code/bridge.log` (an inlined entry discarded it), so a
failed tick leaves a diagnosable trace instead of only a cron mail.

## Step 3 — confirm

**Your shell's `PATH` proves nothing about the scheduler's.** Two checks that
count:

- `env -i PATH=/usr/bin:/bin /bin/sh -c 'command -v memu-claude-code'` — this
  *failing* is exactly why the entry needs its `PATH` line; with that line in
  place the command must resolve from the directories it names.
- The hard check: trigger one run through cron itself (temporarily set the
  schedule a minute ahead, or run `bridge.sh` by hand with
  `env -i PATH=... HOME="$HOME" /bin/sh -c`), then verify **filesystem
  traces** — the session cursor and `jobs/` timestamps moved, and
  `~/.memu/hosts/claude-code/bridge.log` grew — rather than trusting the
  run's own summary. Field data, twice over: scheduled runs in bare
  environments have reported "completed successfully" on a command-not-found.

Report back: where the schedule was registered (crontab/launchd), and the cron in
words (e.g. "hourly at :00 local time"). Mention that the first run only has
work to do once there are new Claude Code sessions since the last run.

## Notes

- **Leftovers run before prepare.** Job files already on disk when the run
  starts are unfinished work — a run that died mid-pipeline, or the install's
  own verify. `prepare` deletes unprocessed job files, and the cursor already
  marks their sessions as seen, so anything skipped at that moment would never
  be minable again; draining leftovers first turns a half-done cycle into
  bounded re-work instead of silent loss.
- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/hosts/claude-code/.session_manifest.claude-code.json`, so each run
  only processes turns it hasn't seen.
- **Ordering is load-bearing.** Memory jobs are numbered before skill jobs, and
  the resource-describe job is last. Always process in ascending numeric order.
- **The working tree is host-scoped.** Everything under
  `~/.memu/hosts/claude-code/` is this adapter's run-scoped working state; other
  memU host adapters (Codex, Cursor, …) have their own and never race with this
  one. The durable backend they all share is selected by `MEMU_MEMORY_MODE` in
  `~/.memu/config.env`; local mode uses the `MEMU_DB` there.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A single "do nothing" job in step 2 is normal, not an error.
