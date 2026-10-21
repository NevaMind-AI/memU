---
name: {{task_doc_name}}
description: Inspect historical Codex bridging schedules and migrate the record trigger to notify.
---

<!-- memu-codex-record: notify-v1 -->

# Codex record trigger and historical schedules

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

Codex record runs now use notify → prepare → headless `codex exec` → commit.
For installation and migration, follow `memu-codex docs install` Part 2.
For removal, follow `memu-codex docs uninstall`. Do not create a recurring
bridging task alongside notify.

The names above identify candidates only. Inspect both Windows Task Scheduler
(in every task folder) and Codex's native scheduling surface when present.
Confirm Codex ownership using the action and arguments, referenced wrapper or
full prompt: the historical pipeline calls `memu-codex prepare`, processes the
numbered self-evolve jobs, then calls `memu-codex commit`. Generic names can
belong to another host. Leave unrelated and ambiguous tasks untouched.

Before changing a confirmed task, save its full definition and enabled/running
state locally, including task path/ID, triggers, principal, working directory,
actions or prompt and referenced wrapper files. Do not delete the old entry
until CLI, backend and notify checks pass. Disable future triggers for the
handoff and wait for any running agent and descendants to finish naturally.
Deleting a registration does not stop the running agent, and old scheduled
agents do not necessarily take notify's workspace lock.

No old task is a normal outcome. Multiple confirmed old tasks must each be
accounted for. A repeated migration must preserve the current notify chain,
retrieval hooks, configuration, memories, logs and session cursors. If a gate
fails, retain/restore the old entry and its original enabled state using the
saved definition; stop future memU notify launches before restoring a schedule.
Never reset the store or cursor to repair a trigger.

Native task export/import and Desktop notify-chain editing require their
supported configuration surfaces. The current CLI does not automate those
operations. If a safe export, handoff or restore cannot be established, report
the migration as pending and keep the recoverable old entry.
