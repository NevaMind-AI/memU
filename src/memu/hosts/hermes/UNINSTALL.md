# Uninstall memU for Hermes Agent

<!-- memu-hermes-install: plugin-v1 -->
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
SOUL.md, and working files are preserved. Any previous memU instruction or
scheduled bridging task requires separate cleanup.

Stop on a nonzero exit and report its diagnostic.
