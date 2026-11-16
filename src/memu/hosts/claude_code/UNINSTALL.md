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

Historical OS/native schedules are outside this command's coverage. Report any
known remaining registrations separately; retain the executable while they need
it. Schedule cleanup requires confirming this host's action, targeted removal
and readback. Preserve other hosts' tasks and user memory.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}.
