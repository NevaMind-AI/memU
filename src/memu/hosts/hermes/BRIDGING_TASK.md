---
name: create-memu-bridging-task
description: Register a scheduled job that bridges the agent's recent Hermes sessions into durable memU memory, skills, and resources. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Hermes)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Hermes sessions into durable memU memory files, skills, and resource
records.

Your goal is to **register a recurring headless Hermes run** whose prompt is the
three-step pipeline below. You are not running the pipeline now.

Part of the full setup in `INSTALL.md` (`memu-hermes docs install`), but usable
on its own.

## What the bridging task does (context)

1. **Prepare** — `memu-hermes prepare` scans new message rows in
   `~/.hermes/state.db` (read-only; sessions ordered by recent activity),
   mirrors the current memU recall files to `~/.memu/hosts/hermes/memory` and
   `~/.memu/hosts/hermes/skill`, snapshots them by content hash, and writes
   numbered **job-instruction files** to `~/.memu/hosts/hermes/jobs/` (`1.txt`,
   `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is
   an allowed, common outcome for any job.
3. **Commit** — `memu-hermes commit` diffs the tracked directories against the
   step-1 snapshot and submits what the agent actually created or changed back
   to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the scheduled
run's prompt must instruct the agent to do it, not shell out to a script.

## Prerequisites

- **memU is installed and `memu-hermes` is on `PATH`.** Verify with
  `memu-hermes doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **Hermes runs headless from cron** with permission to run `memu-hermes` and
  write under `~/.memu/`. If Hermes uses a non-default `HERMES_HOME`, the cron
  environment must export it and the prompt's prepare step must pass
  `--session-dir "$HERMES_HOME/state.db"`.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm before creating.

## Step 2 — register the scheduled run

Create a system cron entry that runs Hermes headless with the pipeline prompt:

```
0 * * * * hermes -p 'Run the memU bridging pipeline. Do the four steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. LEFTOVERS. If ~/.memu/hosts/hermes/jobs/ already contains job files, they are unfinished work from an earlier run (a crash, or the install itself) — process them exactly as step 3 describes, then run:  memu-hermes commit  — and only then continue.  2. PREPARE. Run this exact command with the shell tool:  memu-hermes prepare  — it regenerates ~/.memu/hosts/hermes/jobs/. If the command exits non-zero, stop and report the error.  3. SELF-EVOLVE. List ~/.memu/hosts/hermes/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 4. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  4. COMMIT. Run this exact command with the shell tool:  memu-hermes commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed.'
```

(Adjust the headless invocation to the Hermes CLI the user runs, but keep the
prompt block verbatim.) Nothing in it is machine-specific — the pipeline is
invoked through `PATH` commands.

## Step 3 — confirm

Report back: where the schedule was registered, and the cron in words. Mention
that the first run only has work to do once there are new Hermes sessions since
the last run.

## Notes

- **Leftovers run before prepare.** Job files already on disk when the run
  starts are unfinished work — a run that died mid-pipeline, or the install's
  own verify. `prepare` deletes unprocessed job files, and the cursor already
  marks their sessions as seen, so anything skipped at that moment would never
  be minable again; draining leftovers first turns a half-done cycle into
  bounded re-work instead of silent loss.
- **Idempotent and incremental.** `prepare` tracks a per-session message-count
  cursor in `~/.memu/hosts/hermes/.session_manifest.hermes.json`, keyed by
  session id — messages are append-only per session, so the count-cursor is
  exactly the line cursor the other hosts use.
- **Ordering is load-bearing.** Memory jobs before skill jobs, the
  resource-describe job last. Always ascending numeric order.
- **The working tree is host-scoped.** Everything under `~/.memu/hosts/hermes/`
  is this adapter's run-scoped working state; other memU host adapters never
  race with it. The durable store they all share is the `MEMU_DB` in
  `~/.memu/config.env`.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A "do nothing" job in step 2 is normal, not an error.
