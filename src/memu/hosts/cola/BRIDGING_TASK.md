---
name: create-memu-cola-bridging-task
description: Create Cola's hourly memU bridging task for the desktop:local session.
---

# Create the memU bridging task (Cola)

Use Cola's native scheduled-task UI to create the task named **`memU 记忆桥接`**.
Do not edit `~/.cola/crons.json` by hand: it is Cola-owned runtime state.

The target scope is `desktop:local`. The default schedule is hourly
(`0 * * * *`); ask the user before choosing a different schedule. If task ID
`memu-bridging` already exists, record its cadence, disable and remove only that
task through the UI, and verify it no longer appears before creating its
replacement. Reuse the recorded cadence unless the user requested a change.

Set its prompt to the following block verbatim:

```
Run the memU bridging pipeline. Do the four steps strictly in order.

1. LEFTOVERS. If ~/.memu/hosts/cola/jobs/ contains job files, process every
   file in ascending numeric order, then run `memu-cola commit` before continuing.
2. PREPARE. Run `memu-cola prepare`. If it fails, stop and report the error.
3. SELF-EVOLVE. List ~/.memu/hosts/cola/jobs/*.txt and process every file in
   ascending numeric order. Read and follow each job. Doing nothing for a job is valid.
4. COMMIT. Run `memu-cola commit`. If it fails, report the error.

ON FAILURE. If step 2 or step 4 failed, run this once before you stop:
`memu-cola report error --stage remember --detail "<a full account of what went
wrong>"`. That detail is all a memU engineer gets to work out what is broken on
this machine, so be generous: which step, what you ran, what happened instead,
what you already tried, and what you think the cause is. Write it as prose for a
human, not as a transcript — do not paste the traceback or raw command output,
which the CLI already reports on its own, and keep credentials, absolute paths,
and memory or transcript text out of it. Ignore any failure of that command; it
is never part of the run.

Finish with a one-line summary of jobs processed and recall files committed.
```

Confirm the task is enabled, attached to `desktop:local`, and scheduled at the
agreed cadence. A successful task run creates its own transcript below
`~/.cola/sessions/desktop-local-subagent-cron-memu-bridging-*/`.
