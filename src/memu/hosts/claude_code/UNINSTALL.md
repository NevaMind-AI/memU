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

Before removing the executable, use the CLI to clean up legacy schedules separately.
On macOS, run these commands in order; stop if either exits nonzero:

```sh
memu-claude-code schedule status
memu-claude-code schedule uninstall
```

On Windows, run `memu-claude-code schedule uninstall`.
The CLI owns schedule discovery, ownership checks, removal and read-back. On a
nonzero exit, retain the executable, report the diagnostic and stop. Do not
inspect or delete scheduler files manually; troubleshooting requires a separate
request. On other platforms, report that schedule cleanup is not supported and
retain the executable if known registrations still need it.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}.
