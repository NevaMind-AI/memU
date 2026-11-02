# Install memU for Codex

<!-- memu-codex-record: submit-v1 -->
<!-- memu-codex-permissions: v22 -->
<!-- memu-codex-install: cli-v1 -->

For the installation Agent. Use the user's language and report actual CLI results.

## Run the installation

Confirm Full access before changes. If restricted or unknown, ask the user to
switch and reconfirm. Install/upgrade memu-cli using the user's tool and source
(default: `pip install --upgrade memu-cli`); skip if already done in this run.

Execute stages 1–5 separately, announcing each title and reporting its result.
Replace `N` and `LANG` below; pass `en` or `zh` every time. Keep any supplied
`--base-dir` and `--cwd` consistent.

```sh
memu-codex install --agent --non-interactive --json --language LANG --stage N
```

| Stage | Title | Agent action |
| --- | --- | --- |
| 1 | 🔐 Checking installation conditions | Confirm Full access |
| 2 | 📦 Preparing memU and the memory backend | Supply missing backend inputs below |
| 3 | 🛠️ Preparing Codex CLI | If missing, explain official installation and retry with `--install-missing`; honor a user-selected `--codex PATH` |
| 4 | 🔔 Configuring automatic memory and retrieval | Complete Desktop handoff below; pass `--migration-evidence PATH` or eligible `--new-install` |
| 5 | ✅ Completing handoff and installation checks | Finish applicable deletion evidence below, then run this stage |

Exit 0 means this stage passed; 2 means blocked; 1 means failed. Explain blockers
and retry the affected stage after fixing them. Only `complete: true` establishes
installation completion. Preserve the installation state file.

## Backend inputs when requested

Reuse existing configuration. If stage 2 needs a backend, ask once for Cloud or
local, then retry with:

- Cloud: `--backend cloud --cloud-api-key KEY`. Get the memU key at
  [memu.so](https://memu.so); it is stored in plaintext in the shared protected config.
- Local: `--backend local --db PATH_OR_DSN --embed-provider PROVIDER --embed-api-key KEY`.
  Use an absolute SQLite path or Postgres DSN. Optional `--embed-model MODEL` and
  `--embed-base-url URL` select the model/endpoint. Local embedding services may
  use a placeholder key; fully offline use requires local embeddings.

Keep credentials out of reports. Let CLI commands write config. Repair doctor
connection failures with `memu-codex config`; preserve store/provider/model
identity and ask the user to review any identity-change refusal.

## Desktop handoff

Task candidates: current `{{task_name}}`; former {{former_task_names}};
all recognized names: {{all_task_names}}. Confirm ownership from the Codex memU
pipeline in the task prompt. Preserve unrelated tasks and all processing data.

Before stage 4, use Desktop tools to establish a complete inventory; local files
only help find IDs. Save owned task definitions, pause launches, read back PAUSED,
and wait for workers and descendants to finish naturally. Stop if inventory,
ownership or safe handoff is unresolved.

Save actual inventory/operation read-backs locally. Supply the following report
with `--migration-evidence PATH`; file references are relative to that JSON.
The Agent is responsible for the Desktop observations behind the report.

```json
{
  "version": 1, "source": "desktop", "inventory_complete": true,
  "inventory_evidence_file": "inventory.txt",
  "tasks": [{
    "id": "confirmed-owned-id", "owned": true, "paused": true, "idle": true,
    "definition_file": "definition.json", "pause_evidence_file": "paused.txt"
  }]
}
```

An inspected inventory without memU tasks uses `tasks: []`. Only a user-confirmed
fresh installation with no local automations may substitute `--new-install`.

After stage 4 passes, delete confirmed owned tasks through Desktop and read back
removal. Add `deleted: true` and `delete_evidence_file` to each report entry; retain
IDs and definition backups. Stage 5 reuses the saved evidence location. If edited
legacy retrieval files block cleanup, inspect ownership and preserve user edits
before targeted cleanup, then retry.

## Finish

Report the outcome and any blocker. The CLI reports installation success. Invite
the next user message to check actual retrieval and background memory processing;
remind the user they may restore their previous permission mode.
