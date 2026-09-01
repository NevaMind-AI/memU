---
name: {{task_doc_name}}
description: Register a scheduled pi run that bridges recent sessions into memU.
---

# Create the memU bridging task (pi)

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

The task runs pi headlessly and defaults to hourly at minute 0. Reuse an
existing cadence unless the user requested a change.

## macOS and Linux

Write the following line verbatim to
`~/.memu/hosts/pi/bridge-prompt.txt`:

```text
Run the memU bridging pipeline. Do the four steps strictly in order; do not skip a step even if the previous one looks like it produced nothing.  1. LEFTOVERS. If ~/.memu/hosts/pi/jobs/ already contains job files, they are unfinished work from an earlier run (a crash, or the install itself) — process them exactly as step 3 describes, then run:  memu-pi commit  — and only then continue.  2. PREPARE. Run this exact command with bash:  memu-pi prepare  — it regenerates ~/.memu/hosts/pi/jobs/. If the command exits non-zero, stop and report the error.  3. SELF-EVOLVE. List ~/.memu/hosts/pi/jobs/*.txt and process them in ascending numeric order (1.txt, then 2.txt, …). The count changes every run — always glob and sort. If there are no job files, skip to step 4. For each job file: read it and follow its instructions to the letter. Each job is self-contained and already carries the concrete paths it needs. Emitting no files for a job is a valid outcome; do not invent content.  4. COMMIT. Run this exact command with bash:  memu-pi commit  — it commits whatever the jobs created or changed. If it exits non-zero, report the error.  ON FAILURE. If step 2 or step 4 exited non-zero, run this once before you stop:  memu-pi report error --stage remember --detail "<a full account of what went wrong>"  — that detail is all a memU engineer gets to work out what is broken on this machine, so be generous: which step, what you ran, what happened instead, what you already tried, and what you think the cause is. Write it as prose for a human, not as a transcript — do not paste the traceback or raw command output, which the CLI already reports on its own, and keep credentials, absolute paths, and memory or transcript text out of it. Ignore any failure of that command; it is never part of the run.  Finish with a one-line summary: how many jobs ran (leftovers included) and what was committed.
```

If pi uses a custom session directory, replace only `memu-pi prepare` in that
file with `memu-pi prepare --session-dir <dir>`.

Write `~/.memu/hosts/pi/bridge.sh` and make it executable:

```sh
#!/bin/sh
DIR="$HOME/.memu/hosts/pi"
LOCK="$DIR/.bridge.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT INT TERM
export MEMU_BRIDGING_RUN=1
pi -p "$(cat "$DIR/bridge-prompt.txt")" >> "$DIR/bridge.log" 2>&1
```

Add the directories containing `pi` and `memu-pi` to a crontab `PATH` line,
then register the short entry below. Never inline the long prompt in crontab.

```cron
PATH=<dirname-of-memu-pi>:<dirname-of-pi>:/usr/local/bin:/usr/bin:/bin
```

```cron
0 * * * * $HOME/.memu/hosts/pi/bridge.sh # {{task_name}}
```

Use launchd only if the user explicitly requests it; use `{{task_name}}` as its
label and invoke the same wrapper.

## Windows

Use the existing Task Scheduler helper, which writes the prompt and a
PowerShell wrapper to disk and registers a windowless task:

```powershell
memu-pi schedule install
memu-pi schedule verify
memu-pi schedule status
```

The helper resolves `pi`, runs a headless authentication probe, and registers
`{{task_name}}`. `--interval <minutes>` changes the default 60-minute cadence.
`schedule verify` checks registration and authentication only; it does not run
the S4U task and is not end-to-end proof.

## Verify

Trigger one run and inspect filesystem evidence: `bridge.log` grows and the
session manifest or job timestamps advance. Do not rely only on the agent's
summary. The scheduled pi tool process exports `PI_SESSION_ID`, so `prepare`
records that run as bridge-owned and does not mine it later.
