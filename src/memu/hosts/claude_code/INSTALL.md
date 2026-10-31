# Install memU for Claude Code

<!-- memu-claude-code-scheduling: retired-v1 -->

## Legacy task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

Claude Code uses Submit hooks for retrieval and background memorization. The
scheduled bridging registration procedure is retired. `docs task` is disabled,
and `schedule` exposes only inspection and removal of legacy Windows tasks.

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

## Inspect legacy schedules

**Windows:**

```sh
memu-claude-code schedule status
```

Exit zero means neither recognized task is registered in the memU Task Scheduler
namespace. A nonzero result means tasks remain or inspection failed; read the
diagnostic.

Removing a schedule prevents future launches; it does not establish that an
already-running worker has exited. Wait for a confirmed Claude bridging worker
to finish before installing a replacement or deleting its wrapper. If its state
cannot be established, stop migration and report the unresolved worker.

To remove recognized tasks after that check, the existing maintenance command is:

```sh
memu-claude-code schedule uninstall
memu-claude-code schedule status
```

**macOS/Linux:** the helper does not inspect or modify cron/launchd. Inspect the
user's crontab and `~/Library/LaunchAgents` directly. Identify entries by the
recognized names **and** their Claude-specific action, such as
`~/.memu/hosts/claude-code/bridge.sh` or `memu-claude-code prepare` followed by the
Claude bridging pipeline. An unqualified `memU bridging pipeline` match can also
select another host's task and is insufficient for removal. Remove only confirmed
Claude entries, preserving unrelated tasks and environment lines.

Keep jobs, pending results, session cursors, logs, the store, and other hosts'
files. Full migration and uninstall acceptance remain part of the installation
rollout.
