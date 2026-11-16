# Install memU for pi

<!-- memu-pi-install: extension-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

Run the installer using the existing shared backend:

```sh
memu-pi install --non-interactive --language en
```

For a new backend, pass the user's configuration using `--backend cloud
--cloud-api-key <key>` or `--backend local --db <absolute-path>` with embedding
settings. See `memu-pi install --help`. Use `--language zh` if requested.

The CLI configures and verifies the backend, installs the extension, and checks
its contents. Stop on a nonzero exit and report its diagnostic. On success, run
`/reload` in pi or open a new session, then tell the user automatic retrieval and
background memory are configured.
