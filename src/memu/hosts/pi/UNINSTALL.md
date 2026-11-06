# Uninstall memU for pi

<!-- memu-pi-install: extension-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

1. Remove memU's extension:

   ```sh
   memu-pi remove-prompt-hook
   ```

   Use the same `PI_CODING_AGENT_DIR` if pi uses a custom agent directory.
   Run `/reload` in pi or close the session to unload the extension.

2. Keep the shared `~/.memu/config.env`, memory store, and pi's sessions and
   authentication. Preserve `~/.memu/hosts/pi` unless the user asks to remove
   its working files and logs. Removing the extension stops future hook runs;
   an already running memory worker may finish its current pass.

3. Before removing the package, report the uninstall:

   ```sh
   memu-pi report uninstall
   ```

   On failure, use `memu-pi report error --stage uninstall --detail "<diagnosis>"`.
   Reports are best-effort. Keep credentials and memory content out of reports.

4. Remove `memu-cli` only if no other host adapter uses it. Shared configuration,
   memory, and the event spool stay while another host remains.
