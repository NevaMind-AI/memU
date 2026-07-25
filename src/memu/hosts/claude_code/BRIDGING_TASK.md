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
0 * * * * claude -p 'Run the memU bridging pipeline. Do the four steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. LEFTOVERS. If ~/.memu/hosts/claude-code/jobs/ already contains job files, they are unfinished work from an earlier run (a crash, or the install itself) — process them exactly as step 3 describes, then run:  memu-claude-code commit  — and only then continue.  2. PREPARE. Run this exact command with bash:  memu-claude-code prepare  — it regenerates ~/.memu/hosts/claude-code/jobs/. If the command exits non-zero, stop and report the error.  3. SELF-EVOLVE. List ~/.memu/hosts/claude-code/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 4. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  4. COMMIT. Run this exact command with bash:  memu-claude-code commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed.'
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

## Windows (Task Scheduler)

Steps 2–3 above are cron/launchd — Unix only. **On Windows, do not hand-write a
`schtasks` entry.** The pipeline prompt is ~1000 quoted characters and `schtasks
/TR` splits it on the first space (memU#539); a bare scheduled process also can't
authenticate a desktop-only `claude` (memU#538). Run the helper instead — it does
the whole registration deterministically, so every install is identical and
removable by name:

```
memu-claude-code schedule install     # register the hourly task
memu-claude-code schedule verify      # prove it resolves + authenticates
memu-claude-code schedule status      # last run / next run
memu-claude-code schedule uninstall   # remove it
```

`install` writes the prompt to a file plus a small PowerShell wrapper that reads
it (nothing long ever touches the command line), bakes in the absolute path to
`claude`, and registers a task named `\memU\memu-bridging-claude-code` under an
**S4U** principal — it runs whether or not you're logged in, windowless, and
catches up a run missed while the machine was off. `--interval <minutes>` changes
the cadence (default 60).

Because the scheduled run needs a standalone, headless-authenticated `claude`,
`install` **refuses with guidance** if `claude` isn't on `PATH` or can't
authenticate without a browser. That is the memU#538 verify gate: better to fail at
install than to register a task that reports success and never runs.

> **The credential must be persistent.** The task runs headless under an S4U
> principal (session 0) and inherits only persistent user/machine environment and
> your user profile — **not** a session-only `$env:` export. Use `claude
> setup-token` (writes a token into your profile) or set `CLAUDE_CODE_OAUTH_TOKEN` /
> `ANTHROPIC_API_KEY` as a persistent user variable (`setx`). A token exported only
> in the current shell passes the install-time check yet leaves the task stuck on
> "Not logged in" — the one false-positive the gate can't catch by itself.

Confirm the same way Step 3 does — by filesystem traces, not the run's own
summary: after a run, check that `~/.memu/hosts/claude-code/jobs/` timestamps and
the session cursor advanced.

> Prior art: [jshchnz/claude-code-scheduler](https://github.com/jshchnz/claude-code-scheduler),
> the established Claude Code scheduler (per-OS backends over schtasks/launchd/cron,
> every task namespaced under a scheduler folder). memU diverges for bridging:
> `Register-ScheduledTask` + S4U (windowless, runs logged-out) and a prompt file,
> since the pipeline prompt is too long for the command line.

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
