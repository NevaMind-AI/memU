# Uninstall memU for Hermes Agent

<!-- memu-cleanup: owned-artifacts -->

<!-- memu-hermes-install: soul-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

```sh
memu-hermes uninstall
```

Use the same `HERMES_HOME` as the installed Hermes profile. Uninstall removes
memU's managed SOUL.md block, memorize shell-hook entry and its exact allowlist
approval, and legacy `memu-retrieve` skill. Other SOUL.md
content, sessions, shared memory, working files, and unrelated settings are kept.
Repeating uninstall is safe. Skills installed/refreshed with `.memu-owned.json`
are verified by host and content fingerprint, independent of package/template
version. Unrecorded skills must match packaged content. Edits, extra files,
links and invalid records stop cleanup for ownership review; do not bypass the
check by deleting a directory manually.

A legacy `memu-memory` plugin is inspected for ownership, then removed through
`hermes plugins remove memu-memory`. Directory absence is checked afterward.
Unknown files, symlinks, CLI errors, or incomplete removal stop the operation.
No Hermes Python modules are loaded. Start a fresh session to refresh SOUL.md;
restart running Hermes processes after legacy plugin removal.

Use `memu-hermes remove-instruction` to remove only the retrieval instruction
and legacy skill without full plugin/schedule cleanup.

On Windows, uninstall first inspects and removes recognized legacy Task Scheduler
registrations, checks their wrapper action and working directory, and verifies
absence afterward. Failures stop uninstall with a nonzero exit. Use `--base-dir`
for the original custom workspace. `memu-hermes schedule status` previews the
same check; `memu-hermes schedule uninstall` performs it independently.
Scripts and logs stay.

For Linux/macOS, inspect old crontab or launchd registrations using
`hosts/hermes/bridge\.sh|memU bridging pipeline` as a search hint. Confirm ownership
before removing an entry and verify absence. For Hermes native cron, use
`hermes cron list --all`, inspect the exact job, remove it with
`hermes cron remove <job-id>`, and list again. These schedulers are not covered
by Windows cleanup; unsupported schedule cleanup commands return nonzero.

Stop on a nonzero exit and report its diagnostic.
