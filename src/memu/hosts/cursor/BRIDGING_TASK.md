---
name: create-memu-bridging-task
description: Register a scheduled job that bridges recent Cursor agent sessions into memU memory, skills, and resource submissions. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Cursor)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Cursor agent sessions into memU memory files, skills, and resource
submissions.

Memory and skills are durable in both modes. In cloud mode, the current service
accepts workspace resources from this unchanged pipeline but does not persist or
retrieve them yet.

Your goal is to **register a recurring headless Cursor agent run** whose prompt
is the three-step pipeline below. You are not running the pipeline now.

Part of the full setup in `INSTALL.md` (`memu-cursor docs install`), but usable
on its own.

## What the bridging task does (context)

1. **Prepare** — `memu-cursor prepare` scans new turns under
   `~/.cursor/projects/*/agent-transcripts/` (one JSONL transcript per agent
   session), mirrors the current memU recall files to
   `~/.memu/hosts/cursor/memory` and `~/.memu/hosts/cursor/skill`, snapshots
   them by content hash, and writes numbered **job-instruction files** to
   `~/.memu/hosts/cursor/jobs/` (`1.txt`, `2.txt`, …).
2. **Self-evolve** — the agent opens each job file **in numeric order** and
   follows it: mine a session into user **memory**, mine a session into a
   **skill**, and **describe** the files the sessions touched. "Do nothing" is
   an allowed, common outcome for any job.
3. **Commit** — `memu-cursor commit` diffs the tracked directories against the
   step-1 snapshot and submits what the agent actually created or changed back
   to memU.

Only steps 1 and 3 are code. **Step 2 is real agent work**, so the scheduled
run's prompt must instruct the agent to do it, not shell out to a script.

## Prerequisites

- **memU is installed and `memu-cursor` is on `PATH`.** Verify with
  `memu-cursor doctor`; if it fails, do `INSTALL.md` Part 1 first.
- **`cursor-agent` runs headless.** The scheduled entry invokes
  `cursor-agent -p` non-interactively with permission to run `memu-cursor` and
  write under `~/.memu/`.

## Step 1 — settle the schedule

Ask the user for a schedule if the request doesn't include one. **Default: every
hour**, cron `0 * * * *` (local time). Confirm before creating.

## Step 2 — register the scheduled run

**The crontab's first line is a `PATH`.** cron runs with a bare
`/usr/bin:/bin`; the binaries this entry needs (pipx and npm installs land in
`~/.local/bin` and `/opt/homebrew/bin`) are not there, and the entry dies on
`command not found` before the pipeline starts. Derive it at registration time
and write it **above** the entry:

```
PATH=$(dirname "$(command -v memu-cursor)"):$(dirname "$(command -v cursor-agent)"):/usr/local/bin:/usr/bin:/bin
```

The machine-specific fact lives in the crontab, where machine facts belong —
the pipeline prompt itself stays verbatim.

Create a system cron entry — the default, macOS included (use launchd only if
the user explicitly asks for it) — running:

```
0 * * * * cursor-agent -p 'Run the memU bridging pipeline. Do the four steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. LEFTOVERS. If ~/.memu/hosts/cursor/jobs/ already contains job files, they are unfinished work from an earlier run (a crash, or the install itself) — process them exactly as step 3 describes, then run:  memu-cursor commit  — and only then continue.  2. PREPARE. Run this exact command with bash:  memu-cursor prepare  — it regenerates ~/.memu/hosts/cursor/jobs/. If the command exits non-zero, stop and report the error.  3. SELF-EVOLVE. List ~/.memu/hosts/cursor/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 4. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  4. COMMIT. Run this exact command with bash:  memu-cursor commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed.'
```

The prompt block is fixed; only the cron expression is the user's choice. Nothing
in it is machine-specific — the pipeline is invoked through `PATH` commands.

## Step 3 — confirm

**Your shell's `PATH` proves nothing about the scheduler's.** Two checks that
count:

- `env -i PATH=/usr/bin:/bin /bin/sh -c 'command -v memu-cursor'` — this
  *failing* is exactly why the entry needs its `PATH` line; with that line in
  place the command must resolve from the directories it names.
- The hard check: trigger one run through cron itself (temporarily set the
  schedule a minute ahead, or run the entry's command line by hand with
  `env -i PATH=... /bin/sh -c`), then verify **filesystem traces** — the session
  cursor and `jobs/` timestamps moved — rather than trusting the run's own
  summary. Field data, twice over: scheduled runs in bare environments have
  reported "completed successfully" on a command-not-found.

Report back: where the schedule was registered, and the cron in words. Mention
that the first run only has work to do once there are new Cursor agent sessions
since the last run.

## Notes

- **Leftovers run before prepare.** Job files already on disk when the run
  starts are unfinished work — a run that died mid-pipeline, or the install's
  own verify. `prepare` deletes unprocessed job files, and the cursor already
  marks their sessions as seen, so anything skipped at that moment would never
  be minable again; draining leftovers first turns a half-done cycle into
  bounded re-work instead of silent loss.
- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/hosts/cursor/.session_manifest.cursor.json`.
- **Ordering is load-bearing.** Memory jobs before skill jobs, the
  resource-describe job last. Always ascending numeric order.
- **The working tree is host-scoped.** Everything under `~/.memu/hosts/cursor/`
  is this adapter's run-scoped working state; other memU host adapters never
  race with it. The durable backend they all share is selected by
  `MEMU_MEMORY_MODE` in `~/.memu/config.env`; local mode uses the `MEMU_DB`
  there.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A "do nothing" job in step 2 is normal, not an error.
