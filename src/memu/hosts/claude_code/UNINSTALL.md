# Uninstall memU for Claude Code

<!-- memu-claude-install: cli-v1 -->

For the removal Agent. Use the user's language and run:

```sh
memu-claude-code uninstall --language en
```

Use `--language zh` for Chinese. Wait for this command to exit and report its
result. It removes only memU's retrieval and background memory hook definitions;
it works without the Claude CLI. Other settings and integrations, memory, shared
backend configuration, skills, CLAUDE.md, sessions, jobs, cursors, results and logs
are preserved. Open a new Claude session to pick up the settings change.

The user manages any previously configured memU schedules separately. Do not
remove the package shared by other hosts or erase data as part of this command.
Further cleanup requires an explicit user request.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}.
