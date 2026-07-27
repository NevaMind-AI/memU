---
name: create-memu-cola-bridging-task
description: Create or update Cola's hourly memU bridging task for the desktop:local session.
---

# Create the memU bridging task (Cola)

Use Cola's native scheduled-task UI to create or update the task named
**`memU 记忆桥接`**. Do not edit `~/.cola/crons.json` by hand: it is Cola-owned
runtime state.

The target scope is `desktop:local`. The default schedule is hourly
(`0 * * * *`); ask the user before choosing a different schedule. If a task
with ID `memu-bridging` already exists, update it rather than creating a second
copy.

Set its prompt to the following block verbatim:

```
Run the memU bridging pipeline. Do the four steps strictly in order.

1. LEFTOVERS. If ~/.memu/hosts/cola/jobs/ contains job files, process every
   file in ascending numeric order, then run `memu-cola commit` before continuing.
2. PREPARE. Run `memu-cola prepare`. If it fails, stop and report the error.
3. SELF-EVOLVE. List ~/.memu/hosts/cola/jobs/*.txt and process every file in
   ascending numeric order. Read and follow each job. Doing nothing for a job is valid.
4. COMMIT. Run `memu-cola commit`. If it fails, report the error.

Finish with a one-line summary of jobs processed and recall files committed.
```

Confirm the task is enabled, attached to `desktop:local`, and scheduled at the
agreed cadence. A successful task run creates its own transcript below
`~/.cola/sessions/desktop-local-subagent-cron-memu-bridging-*/`.
