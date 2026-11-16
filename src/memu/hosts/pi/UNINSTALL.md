# Uninstall memU for pi

<!-- memu-cleanup: owned-artifacts -->
<!-- memu-pi-install: extension-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

Run once using the same `PI_CODING_AGENT_DIR` as installation:

```sh
memu-pi uninstall
```

The command removes memU's extension and owned retrieval instructions/skills,
including both global AGENTS filenames. Other instructions, skills, settings,
sessions, shared memory and working files are preserved.

Exit 0 completes this command's cleanup. On a nonzero exit, stop and report the
diagnostic. File checks and deletion belong to the CLI. Run `/reload` or close
the pi session to unload the extension; an active memory worker may finish its pass.

Historical OS schedules are outside this command's coverage. Report any known
remaining registrations separately; retain their executable while needed.
Schedule cleanup requires confirming this host's action, targeted removal and
readback. Preserve other hosts' tasks and user memory.
