# Install memU for Claude Code

<!-- memu-claude-install: cli-v1 -->

For the installation Agent. Use English for prompts, announcements and reports
by default. Use Chinese only when the user explicitly requests Chinese; do not
infer that choice from the language of surrounding conversation. Confirm the session can run
commands and edit Claude user settings; if permissions block the installer, report
the blocker and ask the user to enable the required access.

Install or upgrade memu-cli using the user's tool and source; skip if already done
in this run. Announce `🚀  Installing memU for Claude Code`, then run one command.
Replace LANG with `en` by default, or `zh` when the user explicitly requests Chinese:

```sh
memu-claude-code install --non-interactive --install-missing --json --language LANG
```

The CLI owns backend configuration and verification, CLI preparation,
authentication-status checking, hook registration in `~/.claude/settings.json`
and local settings read-back,
and cleanup of recognized legacy retrieval instructions. Honor user-supplied
`--claude PATH` and `--base-dir` options.

Non-interactive installation checks authentication status but does not send a
model request by default. If the user authorizes a real request test, append
`--test-cli` to the same installation command; it may incur a small charge.
Keep the minimal verification prompt in English (`Reply OK.`).
Report request verification from `cli_request_verified`, independently of
`complete`; successful configuration does not imply a verified model request.

Wait for this command to exit. If a tool returns a running session ID, poll that
same session until exit. Exit 0 with `complete: true` means configuration completed;
exit 2 is blocked, exit 1 failed and exit 130 cancelled. Report failures or lock
conflicts and stop this attempt. Investigations and retries belong to separately
requested troubleshooting. For missing backend inputs, collect the required
choice or credential once and rerun with:

- Cloud: `--backend cloud --cloud-api-key KEY`. Obtain a memU key at
  [memu.so](https://memu.so); it is stored in plaintext in protected shared config.
- Local: `--backend local --db PATH_OR_DSN --embed-provider PROVIDER --embed-api-key KEY`.
  Optional `--embed-model MODEL` and `--embed-base-url URL`. Use an absolute database
  path. Fully offline use requires local embeddings.

If authentication is missing, relay the CLI diagnostic. The user completes login
or provider configuration before retrying. Keep credentials out of reports and
let the CLI write backend config; respect configuration identity protections.

On success, reproduce this report with its emojis, labels and order intact, and
fill placeholders from actual CLI results. Translate the prose only when the user
explicitly requests Chinese. Set CLI request status to `verified` only when
`cli_request_verified` is true; otherwise use `not tested`:

```text
## ✅  memU configuration complete

🧠  Memory backend: <configured backend>.
🛠️  CLI request: <verified / not tested>.
🔗  Retrieval and background memory hooks: configured and read back locally.
💬  Relevant retrieval results can wake Claude after its initial response.

💡  Open a new Claude session to load the hooks. If you previously configured memU
scheduled tasks, pause or remove them yourself to avoid duplicate processing.
💬  A subsequent task can verify actual retrieval and background memory processing.
```

Do not claim that local settings read-back proves the current session has loaded
the hooks or that background memory has completed. For failed or blocked runs,
report the actual diagnostic and completed-state limits.

Legacy task names: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}. The user manages previous schedules.
