# Troubleshooting

Use your host's binary in place of `memu-pi` below.

## Start with the backend

```sh
memu-pi config show
memu-pi doctor
memu-pi retrieve "A topic already saved in memory"
```

Check the resolved mode, database path, embedding provider/model, and the actual diagnostic. Share redacted output when reporting a problem.

## Retrieval returns no results

A new store may be empty. Confirm that memory processing has actually completed, and that writes and retrieval use the same configuration. A different working directory can select a different relative SQLite path; use an absolute path for host adapters.

If you changed the embedding provider or model, existing vectors may be incompatible. Restore the matching configuration or re-index the data deliberately. In programmatic integrations, check the `user` scope used for writes and the `where` filter used for retrieval.

## Backend works, but the agent receives no memory

Run `/reload` or open a new session after installing the pi extension. Open a new Claude Code session after installing hooks. Confirm the host installer completed its registration checks, then test a real turn with a known memory topic.

An empty retrieval does not prove a hook failed. A successful manual retrieval does not prove that the current host session loaded its hooks.

## Background memory is delayed

pi workers use a shared workspace lock and a 30-minute cooldown. Allow the current response and pending retrieval to settle. Inspect the host's diagnostic output before adding another scheduled task; duplicate hooks and schedules can process the same conversations twice.

## Authentication or connection fails

Cloud requires `MEMU_CLOUD_API_KEY`; Local embedding providers use `MEMU_API_KEY` or their provider-specific environment variable. Check the selected mode and endpoint before replacing keys.

For 502 or connection errors, check system proxy settings and whether a local embedding endpoint is being routed through a proxy. `network.no_proxy` in `config.toml` carries `NO_PROXY`; keep exemptions specific to the endpoints that need direct access.

## SQLite reports a lock

SQLite supports one writer at a time. Check for concurrent processes writing to the same file and let the current write finish. Consider Postgres when concurrent writers are a normal workload. Preserve the database while investigating.

## Reporting a problem

Include OS, memU and host versions, the command, expected behavior, redacted diagnostics, and whether the failure is in backend access, registration, retrieval delivery, or background memory. Report version-specific behavior rather than inferring platform support from another machine.
