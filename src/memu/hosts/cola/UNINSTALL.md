# Uninstall memU for Cola

<!-- memu-cleanup: owned-artifacts -->

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

1. In Cola's scheduled-task UI, disable and remove every confirmed memU task
   whose name is in {{all_task_names}}.
   Do not edit `~/.cola/crons.json` directly.
2. Preview `memu-cola remove-instruction --dry-run`, then run
   `memu-cola remove-instruction`. The command removes memU's managed block
   from `~/.cola/memory-bank/MEMORY.md` and its verified retrieval skill from
   `~/.cola/resources/skills/memu-retrieve/`; existing user memory remains intact.
3. Verify the managed block and skill are gone. Installation/refresh records the
   host and content fingerprint in `.memu-owned.json`, allowing unchanged recorded
   skills to be removed across package/template updates. Unrecorded skills must
   match packaged content. Edits, extra files, links or invalid records stop cleanup;
   report the diagnostic and review ownership rather than deleting the directory
   manually. Do not announce completion while a confirmed entry remains.
   Keep `~/.memu/config.env` and its memory store unless the user explicitly asks
   to erase memory.
4. Tell memU the uninstall happened, **before** the package can go — this one
   event is delivered on the spot, and the next step may remove the binary that
   would otherwise have delivered it later:

   ```sh
   memu-cola report uninstall
   ```

   If the uninstall failed or you are stopping early, report that instead:
   `memu-cola report error --stage uninstall --detail "<a full account of what
   went wrong>"`. Be generous with that detail — it is all a memU engineer gets
   to work out what happened here: what would not come out, what you ran, what
   happened instead, what you tried, and what you think the cause is. Detailed,
   not a transcript, though: do not paste the traceback or raw command output,
   which memU reports on its own, and keep credentials, absolute paths, a store
   DSN or endpoint URL, and memory or transcript text out of it. Both commands
   are best-effort: a failed report never blocks an uninstall, and if
   `memu-cola` is already gone there is nothing to report with.
5. Remove `memu-cli` only if no other host adapter still uses it. When it does
   go, remove `~/.memu/events.jsonl` and any `events.jsonl.*.sending`,
   `events.errors`, or `events.dropped` file beside it; when another host remains, leave both — the spool is shared, and
   that host still has those events to deliver.
