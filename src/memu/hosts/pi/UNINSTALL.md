# Uninstall memU for pi

<!-- memu-pi-install: extension-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

```sh
memu-pi uninstall
```

Use the same `PI_CODING_AGENT_DIR` if pi uses a custom agent directory. The CLI
removes memU's extension and preserves pi settings, sessions, shared memory and
working files. Stop on a nonzero exit and report its diagnostic.

Run `/reload` in pi or close the session to unload the extension. An already
running memory worker may finish its current pass.
