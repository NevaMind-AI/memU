# Uninstall memU for Claude Code

<!-- memu-cleanup: owned-artifacts -->
<!-- memu-claude-install: cli-v1 -->

Run once and report the CLI result in the user's language:

```sh
memu-claude-code uninstall --language en
```

Use `--language zh` for Chinese. The command removes memU hooks and owned
retrieval instructions/skills at the default paths, preserving user content,
other integrations, shared configuration and memory. It works without Claude CLI.

Exit 0 completes this command's cleanup. On a nonzero exit, stop and report the
diagnostic. File checks and deletion belong to the CLI. Open a fresh Claude
session to load the settings change.

On macOS, inspect legacy Claude Code schedules separately before removing the executable:

```sh
memu-claude-code schedule status
memu-claude-code schedule uninstall
```

These commands inspect the current/root crontabs, `/etc/crontab`, user/system LaunchAgents and
system LaunchDaemons. They recognize the historical inline `claude -p` prepare/commit action,
not labels alone: the canonical bridge prompt, Claude Code jobs path and both prepare/commit commands must match. Unknown wrappers/actions are preserved and reported for manual inspection.
Status is read-only and reports checked, loaded and running launchd domains; a retained plist may exist without a loaded job. uninstall removes only confirmed Claude Code bridge registrations and
reads them back. Permission/query/removal errors return nonzero; partial cleanup is reported,
never as complete success. Run with the required owning-user/system permissions rather than
assuming an inaccessible registration is absent. The hooks, memory, shared configuration,
and other hosts' registrations are preserved. `--base-dir` does not restrict OS schedule discovery.

A loaded job with a PID is left running: future launches are disabled, its plist is retained,
and cleanup returns nonzero. Let it exit naturally, then retry; do not kill a user's agent.
Shared `/Library/LaunchAgents` plists are inspected in the current user domains but preserved for manual all-user domain verification. Root/system-daemon and crontab cleanup requires owning-user privileges.
Crontab removal prevents future runs without terminating an existing process. Concurrent
crontab/file changes detected before replacement abort that item; the OS APIs do not provide
a cross-process compare-and-swap guarantee.

Other platforms/native schedules remain outside this command's coverage. Report any
known remaining registrations separately; retain the executable while they need
it. Schedule cleanup requires confirming this host's action, targeted removal
and readback. Preserve other hosts' tasks and user memory.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}.
