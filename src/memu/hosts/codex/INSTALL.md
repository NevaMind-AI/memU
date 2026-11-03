# Install memU for Codex

<!-- memu-codex-record: submit-v1 -->
<!-- memu-codex-permissions: v22 -->
<!-- memu-codex-install: cli-v2 -->

For the installation Agent. Use the user's language.

## Check permissions and install

Confirm the session's effective sandbox mode is `danger-full-access`. If restricted
or unknown, ask the user to enable Full access and reconfirm before changes.
Install/upgrade memu-cli using the user's tool and source (default:
`pip install --upgrade memu-cli`); skip if already done in this run.

The terminal installer uses emoji progress headings, concise backend results and
an elapsed time measured after language selection. Download and installer failures
include the cause and a suggested next action. Use `--json` for machine-readable
progress.

Announce `🚀 Installing memU for Codex` in the user's language, then run **one
command**. Replace `LANG` with `en` or `zh` for this invocation:

```sh
memu-codex install --non-interactive --install-missing --json --language LANG
```

The CLI reuses the existing backend, runs doctor, prepares the standalone Codex CLI,
registers and verifies both memory hooks, and cleans up recognized legacy retrieval
entries. Honor user-supplied `--codex PATH`, `--base-dir` and `--cwd` options.

Wait for the same command to exit. If the tool returns a running session ID, poll
that session until exit; partial output is still an active installation. Exit 0
with `complete: true` means installation succeeded. Exit 2 is blocked; exit 1 is
failed. If another installer holds the installation lock, report that installation
is blocked and end this attempt. Leave process inspection, worker-status polling,
and retrying to a separate user-requested troubleshooting session. For other
failures, report the diagnostic and stop; missing backend inputs are handled below.
Ctrl+C returns exit 130 with `status: cancelled`; EOF returns exit 2 with an
input-ended diagnostic. Neither means installation completed. Changes from
completed steps may remain.

## Missing backend inputs

If the CLI reports missing configuration, ask once for the required choice or
credential, then rerun the installer with:

- Cloud: `--backend cloud --cloud-api-key KEY`. Get a memU key at
  [memu.so](https://memu.so); it is stored in plaintext in the shared protected config.
- Local: `--backend local --db PATH_OR_DSN --embed-provider PROVIDER --embed-api-key KEY`.
  Use an absolute SQLite path or Postgres DSN. Optional `--embed-model MODEL` and
  `--embed-base-url URL` select the model/endpoint. Local embedding services may
  use a placeholder key; fully offline use requires local embeddings.

Keep credentials out of reports. Let the CLI write config. Preserve existing
store/provider/model identity and respect configuration-change refusals.

## Report the result

Use this compact report on success. Keep the emoji and Markdown heading, translate
the text into the user's language, and fill values only from actual CLI results:

```text
## ✅ memU installation complete

🧠 Memory backend: <configured backend>.
🔗 Automatic retrieval and background memory hooks: registered and trusted.

💡 If you use Codex Desktop and previously set up memU scheduled tasks yourself,
you can now pause or remove them to avoid processing memory twice.

💬 Send another message to check actual retrieval and background memory processing.
🔐 You may now restore your previous permission mode.
```

For a blocked or failed installation, use `## ⚠️ memU installation blocked` or
`## ❌ memU installation failed` in the user's language, followed by the actual
diagnostic. Only claim successful checks confirmed by the CLI.

Task-name references: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}. The user manages existing scheduled tasks
after installation.
