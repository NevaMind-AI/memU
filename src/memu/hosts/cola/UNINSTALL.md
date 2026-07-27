# Uninstall memU for Cola

1. In Cola's scheduled-task UI, disable and remove the `memu-bridging` task.
   Do not edit `~/.cola/crons.json` directly.
2. Run `memu-cola remove-instruction`. This removes only memU's managed block
   from `~/.cola/memory-bank/MEMORY.md`; existing memory remains intact.
3. Remove `~/.cola/resources/skills/memu-retrieve/` if it remains after the
   command. Keep `~/.memu/config.env` and its memory store unless the user
   explicitly asks to erase memory. Remove `memu-cli` only if no other host
   adapter still uses it.
