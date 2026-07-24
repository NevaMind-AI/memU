ADR 0012: Cloud-Backed Memory Behind the Existing CLI

- Status: Accepted
- Date: 2026-07-24
- Builds on: ADR 0008 (two host seams), ADR 0009 (one CLI/config surface)
- Scope: selecting local or hosted execution for the three agentic memory
  operations. It does not change `MemoryService`, storage repositories, or the
  host command surface.

## Context

Every `memu` and `memu-<host>` operation currently constructs a local
`MemoryService`. That requires a local database plus an embedding provider even
when the hosted memU service already exposes the same three operations over its
API-key-authenticated v4 API.

Creating separate cloud binaries would duplicate every host command, retrieval
instruction, scheduled task, and installation path. Adding HTTP behavior to
`MemoryService` would instead turn the local composition root into two unrelated
runtime roles and weaken its embedding-only, storage-pluggable boundary.

## Decision

### One structural capability boundary

`AgenticMemoryBackend` is a structural protocol containing exactly
`list_all_recall_files`, `progressive_retrieve`, and `commit_results`.
`MemoryService` already satisfies it and remains the local in-process
implementation. `CloudMemoryClient` implements it by forwarding requests to:

- `GET /api/v4/memory/`
- `POST /api/v4/memory/search`
- `POST /api/v4/memory/`

The cloud client returns successful response dictionaries unchanged. It owns
Bearer authentication, explicit timeouts, structured cloud errors, and bounded
retries for transient failures. None of those concerns enter `memu.app`.

### One selector for every caller

`build_agentic_memory_backend_from_env()` is the only backend selector used by
the main CLI, host retrieval, bridging prepare/commit, and doctor.
`MEMU_MEMORY_MODE` accepts `local` or `cloud`; absent means `local`, preserving
existing installs.

Cloud configuration is separate from local embedding configuration:

```env
MEMU_MEMORY_MODE=cloud
MEMU_CLOUD_API_KEY=<memu-api-key>
MEMU_CLOUD_BASE_URL=https://api.memu.so/api/v4/memory/
```

The base URL has the production value above as its default and remains
overridable for compatible deployments. Users obtain a memU API key by
registering at [memu.so](https://memu.so). `MEMU_BASE_URL` and `MEMU_API_KEY`
keep their existing local-embedding meaning.

The main `memu` CLI retains its local database/embedding flags. They are passed
as local-mode overrides to the shared selector; cloud mode does not construct a
local store as a side effect.

### Explicit default owner scope

Cloud requests always send both `user_id` and `agent_id`. Missing, blank, or
`None` values become the literal `default`. Cloud reads accept only exact
`user_id` and `agent_id` filters because the public API cannot represent local
repository operators such as `user_id__in`; unsupported filters fail rather
than silently widening scope.

### Resource compatibility is visible, not forked

The bridging pipeline remains identical in both modes: it prepares resource
work and submits `commit_results.resource`. The current cloud API accepts that
field for wire compatibility but returns an empty `resources` list because it
does not persist workspace resources yet. Doctor and installation documentation
state this limitation explicitly; memory and skill recall files are durable.

## Consequences

Positive:

- Existing agent commands, scheduled tasks, and retrieval instructions work in
  either mode without rewrites.
- `MemoryService` keeps its three-method public surface and remains free of HTTP
  and authentication behavior.
- Cloud credentials cannot be confused with embedding-provider credentials.
- An old config with no mode keeps its local database and embedding space.

Costs:

- The cloud client has a deliberately narrower `where` vocabulary than a custom
  local `UserConfig.model`.
- Resource-description jobs still run in cloud mode even though the service
  currently does not persist their output. This preserves one bridging
  pipeline at the cost of temporary redundant work.
- The project API key may be stored as plaintext in `~/.memu/config.env`; guides
  require user-only file permissions and process-environment overrides remain
  available.

## Out of scope

- Dashboard cookie/CSRF APIs
- OAuth, browser login, or OS keychain integration
- Local-to-cloud memory migration
- Cloud resource persistence
- New CLI binaries
- Storage protocol, backend, or migration changes
