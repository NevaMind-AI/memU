# Install memU for Codex

<!-- memu-codex-record: submit-v1 -->
<!-- memu-codex-permissions: v22 -->
<!-- memu-codex-install: cli-v1 -->

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration: {{all_task_names}}

This guide is for the installation Agent. Use the user's language. The Python
`memu-codex install` command owns backend configuration, executable preparation,
registration and installation checks. Report actual results between stages.

## 1. 🔐 Check installation conditions

Confirm the current session has Full access before making installation changes.
If access is restricted or unknown, ask the user to switch to Full access, then
reconfirm the effective mode before continuing. CLI failures still need fixing.

If memu-cli was already installed or upgraded in this run, reuse it. Otherwise
use the user's package manager and source; the default is:

```sh
pip install --upgrade memu-cli
```

Run the first stage:

```sh
memu-codex install --agent --non-interactive --json --stage 1
```

Use the same `--base-dir` and `--cwd` throughout if supplied. Each invocation
returns one stage's result. Exit 0 means that stage passed; 2 means blocked;
1 means failed. Only a result with `complete: true` establishes installation
completion. Stop on a blocker and explain its next action.

## 2. 📦 Prepare memU and the memory backend

```sh
memu-codex install --agent --non-interactive --json --stage 2
```

Existing configuration is reused and checked with doctor. If configuration is
missing, ask once for Cloud or local storage, then repeat this stage with the
necessary options:

- Cloud: `--backend cloud --cloud-api-key <memU key>`. Obtain a key at
  [memu.so](https://memu.so). It is stored in plaintext in the shared protected
  configuration file. Cloud persists memory and skills; workspace resources
  are accepted but currently not persisted or retrieved.
- Local: `--backend local --db <absolute SQLite path or Postgres DSN>
  --embed-provider <provider> --embed-api-key <embedding key>`.
  Optional `--embed-model` and `--embed-base-url` select the embedding model and
  endpoint. A local OpenAI-compatible embedding server can use a placeholder
  key. Local storage is fully offline only with a local embedding provider.

Keep credentials out of reports. Let the CLI write configuration. If doctor
fails, repair connectivity using `memu-codex config`; preserve the existing
store/provider/model identity. An identity-change refusal needs user review.

## 3. 🛠️ Prepare Codex CLI

```sh
memu-codex install --agent --non-interactive --json --stage 3
```

Use `--codex <path>` when the user selected an executable. If the CLI reports
that Codex is missing, explain the official installation and retry with
`--install-missing`. Reuse the discovered executable; let Python manage the
installer and startup check. The default `~/.codex` supplies shared CLI/Desktop
configuration and authentication, including for registered background commands.

## 4. 🔔 Configure automatic memory and retrieval

First resolve old tasks through Codex Desktop tooling. Task names above are
candidates; confirm the prompt invokes this host's memU pipeline before claiming
ownership. Preserve unrelated tasks. Local automation files help discover IDs;
if they do not establish a complete inventory, obtain Desktop read-back evidence
or report the blocker. Terminal CLI does not manage Desktop tasks independently.

For every owned old task, save its complete definition, pause only its launches
through Desktop, read back PAUSED, and wait for existing workers and descendants
to finish naturally. Preserve the definition and all pipeline state. Do this
before registering replacement hooks. If safe handoff cannot be confirmed, stop.

Save the actual inventory and operation results as local evidence files. Supply
an evidence JSON document using paths relative to that document:

```json
{
  "version": 1,
  "source": "desktop",
  "inventory_complete": true,
  "inventory_evidence_file": "inventory.txt",
  "tasks": [{
    "id": "confirmed-owned-task-id",
    "owned": true,
    "paused": true,
    "idle": true,
    "definition_file": "task-definition.json",
    "pause_evidence_file": "task-paused.txt"
  }]
}
```

The CLI validates this Agent report's structure, local artifacts and continuity;
it cannot independently authenticate Desktop results. Supply observations, not
invented confirmations. An inspected inventory with no memU tasks uses an empty
`tasks` array. Use `--new-install` only when the user confirms a new installation
and there are no local automations; lack of inventory is not that confirmation.

```sh
memu-codex install --agent --non-interactive --json --stage 4 --migration-evidence /path/to/migration.json
```

For a confirmed new installation, substitute `--new-install` for the evidence
option. The CLI registers and verifies both handlers; preserve its state file.

## 5. ✅ Complete handoff and installation checks

Only after stage 4 passes, delete the confirmed owned tasks by ID using Desktop
and read back their removal. Keep their saved definitions. For each evidence
entry add `deleted: true` and `delete_evidence_file` pointing to its actual
removal read-back. Keep the same inventory, IDs and original definitions.

```sh
memu-codex install --agent --non-interactive --json --stage 5
```

The saved state retains Agent mode and the evidence location. The CLI checks
hook configuration, trust, backend continuity and preserved pipeline files,
then removes the owned old retrieval skill and managed instruction pointer.
Ambiguous ownership or extra files block cleanup. Success is reported once by
the CLI; no separate `report install` is needed. Failed registration retains old
task definitions and state so the failed stage can be retried safely.

Give a concise outcome, mention any unresolved task migration, and remind the
user they can restore their previous permission mode. Invite the next user
message for actual retrieval delivery and background memory acceptance. Runtime
model execution is a separate check; installation does not wait for it.

## Direct terminal installation

A user running `memu-codex install` gets all five stages and interactive backend
and missing-program prompts. It asks the user to pause old memU tasks in Desktop
and leaves their migration for a Desktop Agent. CLI integration can complete
with `migration: desktop_deferred`; do not describe that as completed migration.
