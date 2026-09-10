# Uninstall memU for pi

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

1. Remove only pi's memU schedule:
   - cron/launchd: remove the entry invoking `~/.memu/hosts/pi/bridge.sh` or
     labeled `{{task_name}}`;
   - Windows: run `memu-pi schedule uninstall`, then confirm
     `memu-pi schedule status` reports not registered.
2. Run `memu-pi remove-instruction`. If installation used custom `--path` or
   `--skills-dir`, pass the same values. This removes only memU's managed block
   and `memu-retrieve` skill; user content remains.
3. Keep `~/.memu/config.env`, its memory store, and
   `~/.memu/hosts/pi/.session_manifest.pi.json` unless the user explicitly asks
   to erase memory. Remove the other files under `~/.memu/hosts/pi/`.
4. Before removing the package, report the uninstall:

   ```sh
   memu-pi report uninstall
   ```

   On failure, use `memu-pi report error --stage uninstall --detail "<what
   failed, what was tried, and the likely cause>"`. Reports are best-effort and
   must not contain credentials, absolute paths, command output, memory, or
   transcript text.
5. Remove `memu-cli` only if no other host adapter uses it. The event spool and
   shared memory configuration also stay while another host remains.
