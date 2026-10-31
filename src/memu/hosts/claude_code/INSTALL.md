# Install memU for Claude Code

<!-- memu-claude-code-scheduling: retired-v1 -->

## Legacy task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

Claude Code uses Submit hooks for retrieval and background memorization. The
scheduled bridging registration procedure is retired and `docs task` is disabled.

**Installation rollout is incomplete.** CLI-managed hook installation and the
complete installation acceptance procedure are tracked in
[the installation rollout](https://github.com/NevaMind-AI/memU/pull/772).
Do not report a new installation complete based on this guide or recreate a
scheduled task. Existing hook configuration can be inspected against the
[retrieval reference](https://github.com/NevaMind-AI/memU/blob/claude-dev/docs/retrieval.md#claude-code-prompt-hook).

## Inspect the existing memory configuration

These commands read the configured backend and check its connectivity:

```sh
memu-claude-code config show
memu-claude-code doctor
```

Keep the existing store, embedding identity, and shared `~/.memu/config.env`.

## Migrate legacy schedules

Use the platform's scheduler tools to inventory existing registrations:

- **Windows:** inspect Task Scheduler with `Get-ScheduledTask`, including task
  paths and actions. Historical registrations may use different task paths;
  record the exact task path and name for each confirmed entry.
- **Linux/macOS cron:** inspect the user's crontab with `crontab -l`.
- **macOS launchd:** inspect loaded user jobs with `launchctl` and their plist
  definitions under `~/Library/LaunchAgents`.

Use the recognized names as candidates, then confirm the action belongs to the
Claude adapter: its `~/.memu/hosts/claude-code/bridge.sh` or `memu-bridge.ps1`
wrapper, or an inline Claude prepare / self-evolve / commit pipeline. A name or
an unqualified `memU bridging pipeline` match alone is insufficient for removal.
Leave unrelated and ambiguous entries untouched. Unavailable inventory is an
unresolved migration, not evidence that tasks are absent.

Pause or disable confirmed registrations to prevent future launches. Wait for
any running old worker and its descendants to finish naturally before installing
a replacement or deleting its wrapper. Do not kill workers or run new background
memorization alongside them. If their state cannot be established, stop migration.

Once idle, remove only the confirmed registrations with the platform's scheduler
tools, then query again to verify their absence and preservation of unrelated
entries. For confirmed Windows registrations in the helper's memU namespace,
the existing cleanup command remains available:

```sh
memu-claude-code schedule uninstall
```

This helper removes recognized Windows tasks and their generated wrapper/prompt
files; it does not establish worker completion or inspect registrations in other
locations. On Linux/macOS, it reports that no cleanup was performed and refers to
the cron/launchd procedure above. Verify removal with the platform's scheduler
tools before declaring the migration complete.

Delete only confirmed generated wrappers and prompt files after the registration
check. Keep jobs, pending results, formal and pending session cursors, self-session
records, logs, the store, shared config, and other hosts' files. Full migration
and installation acceptance remain part of the installation rollout.
