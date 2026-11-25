# ADR 0026: Readable shared TOML configuration with automatic legacy migration

- Status: Proposed
- Date: 2026-11-25
- Builds on: [ADR 0017](0017-config-env-as-a-command.md), [ADR 0012](0012-cloud-backed-agentic-backend.md)
- Chinese: [中文](0026-shared-toml-config.zh.md)
- Scope: shared CLI/host configuration, installation commands, installed-user upgrades.

## Context

The current `~/.memu/config.env` mirrors process environment names. Uppercase,
flat `MEMU_*` names repeat the application namespace and hide the relationship
between Cloud credentials, embedding credentials, retrieval settings and host
settings. `init` exposes only a subset; users must discover many supported keys
in source or documentation and add them themselves. Adding another switch to
that format would continue the same usability problem.

Users already have credentials, database locations, embedding models, thresholds,
proxy settings and a stable client identity. An upgrade must retain them without
requiring re-entry or changing the store/embedding space. The migration must also
work when different hosts start concurrently.

## Decision

Use `~/.memu/config.toml`, with lowercase grouped keys. Keep the shared environment
name API internally so CLI flags, host adapters and backend construction continue
to use one resolver. `config_schema.py` defines the mapping; `config_template.toml`
provides editable common values and commented advanced examples. Values which
select a store or embedding model are never inferred during migration.

Examples include `cloud.api_key`, `embedding.api_key`, `retrieval.cloud.min_score.short`,
`network.proxy`, `telemetry.enabled`, `hosts.cowork.roots` and `sources.docs`.
Scores and batch sizes use numbers, switches use booleans, and Cowork roots use an
array. Empty optional strings retain existing unset/disable semantics. Advanced
source, debug and Cowork settings now read the shared file as well as the environment.

### Upgrade and precedence

1. On first file access, migrate an existing dotenv if the TOML target is absent.
   Package installation itself does not execute migration code. `config show` may
   therefore perform the one-time upgrade before reporting the configuration.
2. Parse the original using the existing Windows BOM/encoding support. Convert
   known keys, collapse the legacy embedding-provider alias, and validate types.
   Read disk values only; never persist an ephemeral shell override.
3. Hold a cross-process file lock, recheck the target, then write a temporary file
   beside it and publish by atomic replacement. Preserve the original dotenv
   byte-for-byte as the rollback copy. Only the lock holder publishes migration.
4. An existing TOML is authoritative, without per-key fallback to the old file.
   A failed automatic migration warns with the exception class, then reads the
   original configuration. An invalid existing TOML is an error, not a reason to
   silently switch back to old credentials or another store.
5. Explicit environment variables still override the file, including an empty
   value where the setting supports disabling behavior. The legacy provider
   environment alias also overrides the migrated file value.

`MEMU_CONFIG` selects an explicit TOML target. Existing `MEMU_CONFIG_ENV` still
selects the migration source; absent an explicit target, migrate beside that
source with a `.toml` suffix. If the source already has that suffix, use
`.migrated.toml` to avoid overwriting it. The default target is `~/.memu/config.toml`.

### Preservation and writes

Unknown old assignments remain string values under `[legacy]` and are reported by
key name only. This keeps custom/future settings available through the existing
resolver. Original comments remain in the retained source. Subsequent TOML writes
preserve TOML comments, order, unknown tables and unrelated user settings.

The stable client ID moves unchanged to a sibling `.state.toml` file; it is not
an editable configuration choice. Existing command/event callers use the same
internal key API. Internal child-process markers remain process variables.

Config and state files use atomic UTF-8 writes with `fsync`. POSIX permissions
remain `0700` for newly created directories and `0600` for files. Windows files
inherit ACLs, as before; no stronger Windows permission claim is made.

Use `tomlkit` for comment-preserving TOML edits and `filelock` for process locking.
All writes, including command updates after migration, use the same lock.

## Consequences and validation

- Installed users keep their settings and can immediately edit the new format.
- New installs see common choices and discover advanced ones in the generated file.
- Downgrading can still read the retained dotenv, but TOML edits are not synchronized
  back to it; check current values before downgrading.
- Retrieval scheduling, model calls, database schemas and embedding behavior are
  outside this migration. The query-extraction policy PR adapts afterward.
- README and the public docs-site configuration guide are coordinated separately.
- Test migration/idempotence, all public mappings, aliases, typed validation,
  credential-safe diagnostics, empty disable values, encoding, rollback on write
  failure, concurrent processes/writers and existing installation guards.
