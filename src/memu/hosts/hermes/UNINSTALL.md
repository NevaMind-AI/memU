# Uninstall memU for Hermes Agent

<!-- memu-cleanup: owned-artifacts -->
<!-- memu-hermes-install: soul-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

Run once using the same `HERMES_HOME` as installation:

```sh
memu-hermes uninstall
```

The CLI removes memU's managed retrieval instruction/skill, memorize shell hook
and approval, and verified legacy plugin. On Windows it also removes recognized
legacy Task Scheduler registrations and verifies absence. Use `--base-dir` for
the original custom workspace. Other user content, settings, sessions, shared
memory, working files and logs are preserved.

Exit 0 completes this command's cleanup. On a nonzero exit, stop and report the
diagnostic. File and registration checks belong to the CLI. Start a fresh session;
restart running Hermes processes if the CLI reports legacy plugin removal.

Linux/macOS OS schedules and Hermes native cron are outside this command's
coverage. Report known remaining registrations separately. For native cron,
`hermes cron list --all`, confirm the exact memU job, use
`hermes cron remove <job-id>`, and list again. Historical Unix registrations may
reference `hosts/hermes/bridge\.sh|memU bridging pipeline`; confirm this host's
actual action before targeted removal. Preserve unrelated tasks and user memory.
