# Install memU for pi

<!-- memu-pi-install: extension-v1 -->
<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->

> **Audience: the agent.** Use the installer below and report its result. Reuse
> the user's existing pi environment and shared memU backend.

## Install

With memu-cli installed and pi available on PATH, run:

```sh
memu-pi install --non-interactive --language en
```

The installer checks pi and the extension destination, configures or reuses the
shared memory backend, verifies retrieval, and installs the packaged extension.
It reads back the extension to verify the Python executable and working directory.

Pass any backend inputs the user supplied to this invocation. For a new Cloud
configuration:

```sh
memu-pi install --non-interactive --language en --backend cloud --cloud-api-key <memu-api-key>
```

For local memory, supply an absolute database path and the embedding settings:

```sh
memu-pi install --non-interactive --language en --backend local --db /absolute/path/memu.sqlite3 --embed-provider openai --embed-api-key <embedding-key>
```

Use `--embed-model` and `--embed-base-url` when the embedding service requires
them. Existing backend settings from another host are reused by default.
Configuration is written through memU's configuration commands.

Use `--language zh` when the user explicitly requests Chinese. Interactive
terminal users can run bare `memu-pi install`. Add `--json` for machine-readable
progress; exit code zero and a final `complete: true` indicate success.

## Activate

Run `/reload` in pi or open a new session. The extension is installed at:

```text
~/.pi/agent/extensions/memu-retrieval.ts
```

`PI_CODING_AGENT_DIR` selects a custom pi agent directory. `--base-dir` selects
memU's working directory, defaulting to `~/.memu/hosts/pi`.

User submissions start retrieval in the background. Once the answer and pending
retrieval have settled, saved conversations can be processed into durable memory
by a background pi worker. The worker uses the active session's model.

## Report

Tell the user the selected backend, that extension readback verification passed,
and that `/reload` or a new session activates automatic retrieval and background
memory. Report a partial setup if the installer stops before completion, and
include its actionable diagnostic. Keep credentials and memory content out of
reports.

To remove the extension, run `memu-pi remove-prompt-hook` and reload pi.
