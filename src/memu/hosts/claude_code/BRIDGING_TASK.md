---
name: create-memu-bridging-task
description: Register a scheduled job that bridges the agent's recent Claude Code sessions into durable memU memory, skills, and resources. Runs the prepare → self-evolve → commit pipeline on a schedule (default: every hour).
---

# Create the memU bridging scheduled task (Claude Code)

Use this when the user asks to **set up (or change) the recurring memU
"bridging" task** — the job that periodically turns what the agent recently did
in its Claude Code sessions into durable memU memory files, skills, and resource
records.

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
- **A headless run can execute the pipeline.** The scheduled run invokes
  `claude -p` non-interactively, so the commands and paths the pipeline touches
  must be pre-authorized: allow `Bash(memu-claude-code *)` and writes under
  `~/.memu/` in `~/.claude/settings.json` permissions. Do **not** reach for a
  blanket permission-skip flag; the pipeline needs exactly those two things.

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
PATH=$(dirname "$(command -v memu-claude-code)"):$(dirname "$(command -v claude)"):/usr/local/bin:/usr/bin:/bin
```

The machine-specific fact lives in the crontab, where machine facts belong —
the pipeline prompt itself stays verbatim.

Create a system cron entry — the default, macOS included (use launchd only if
the user explicitly asks for it) — that runs Claude Code headless with the
pipeline prompt:

```
0 * * * * claude -p 'Run the memU bridging pipeline. Do the three steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. PREPARE. Run this exact command with bash:  memu-claude-code prepare  — it regenerates ~/.memu/hosts/claude-code/jobs/. If the command exits non-zero, stop and report the error.  2. SELF-EVOLVE. List ~/.memu/hosts/claude-code/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 3. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  3. COMMIT. Run this exact command with bash:  memu-claude-code commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  Finish with a one-line summary: how many jobs ran and what was committed.'
```

The prompt block is fixed; only the cron expression is the user's choice. Nothing
in it is machine-specific — the pipeline is invoked through `PATH` commands.

## Step 3 — confirm

**Your shell's `PATH` proves nothing about the scheduler's.** Two checks that
count:

- `env -i PATH=/usr/bin:/bin /bin/sh -c 'command -v memu-claude-code'` — this
  *failing* is exactly why the entry needs its `PATH` line; with that line in
  place the command must resolve from the directories it names.
- The hard check: trigger one run through cron itself (temporarily set the
  schedule a minute ahead, or run the entry's command line by hand with
  `env -i PATH=... /bin/sh -c`), then verify **filesystem traces** — the session
  cursor and `jobs/` timestamps moved — rather than trusting the run's own
  summary. Field data, twice over: scheduled runs in bare environments have
  reported "completed successfully" on a command-not-found.

Report back: where the schedule was registered (crontab/launchd), and the cron in
words (e.g. "hourly at :00 local time"). Mention that the first run only has
work to do once there are new Claude Code sessions since the last run.

## Notes

- **Idempotent and incremental.** `prepare` tracks a per-session line cursor in
  `~/.memu/hosts/claude-code/.session_manifest.claude-code.json`, so each run
  only processes turns it hasn't seen.
- **Ordering is load-bearing.** Memory jobs are numbered before skill jobs, and
  the resource-describe job is last. Always process in ascending numeric order.
- **The working tree is host-scoped.** Everything under
  `~/.memu/hosts/claude-code/` is this adapter's run-scoped working state; other
  memU host adapters (Codex, Cursor, …) have their own and never race with this
  one. The durable store they all share is the `MEMU_DB` in
  `~/.memu/config.env`.
- **Failure handling.** Steps 1 and 3 are the only failure points that should
  abort the run. A single "do nothing" job in step 2 is normal, not an error.
