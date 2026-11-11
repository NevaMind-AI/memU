# Uninstall memU for Hermes Agent

<!-- memu-hermes-install: plugin-v2 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

```sh
memu-hermes uninstall
```

Use the same `HERMES_HOME` as the installed Hermes profile. The CLI checks
ownership before delegating removal of the `memu-memory` plugin and its
activation entries to `hermes plugins remove`. Unknown files or symlinks stop
removal so they can be inspected. Repeating uninstall is safe.

Restart Hermes to unload the plugin. An active memory worker may finish its
current pass. Hermes settings for other plugins, sessions, shared memory,
SOUL.md, and working files are preserved. Previous memU instructions require
separate cleanup.

On Windows, uninstall first inspects and removes recognized legacy Task Scheduler
registrations, checking their wrapper action and working directory and verifying
absence afterward. Inspection, ownership, deletion, and readback failures stop
uninstall with a nonzero exit. Use `--base-dir` for the original custom workspace.
`memu-hermes schedule status` previews the same check;
`memu-hermes schedule uninstall` performs it independently. Scripts and logs stay.

For Linux/macOS, inspect the old crontab or launchd registration using
`hosts/hermes/bridge\.sh|memU bridging pipeline` as a search hint, then confirm
ownership before removing an entry and verify its absence. For Hermes native
cron, use `hermes cron list --all`, inspect the exact memU bridging job, remove it
with `hermes cron remove <job-id>`, and list again. These schedulers are not covered
by the Windows cleanup command; on other platforms it returns a nonzero exit.

Stop on a nonzero exit and report its diagnostic.
