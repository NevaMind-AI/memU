# 0023: Remove Cola and Generic Host Adapters

## Status

Accepted. Supersedes [ADR 0011](0011-generic-host-adapter.md) for current host support.

## Context

Host installation is moving toward explicit lifecycle hooks, as described in
[ADR 0022](0022-host-memory-hooks.md). Installing an integration requires knowing
the host's hook registration, session identity, context delivery and uninstall
behavior. The generic adapter discovers files for an unknown host; that discovery
cannot establish or verify a host-specific hook installation contract. Keeping
it would require maintaining a separate integration path.

The project also lacks capacity to maintain and verify the current Cola adapter.
Support for Cola or another new host should be introduced through a contributor's
PR with a concrete implementation of the current hook installation contract,
tests and installation/uninstallation documentation.

## Decision

Remove the Cola and generic adapter packages, CLI registrations and specific
tests. Installation routing lists supported hosts explicitly and stops unlisted
hosts before package installation. Existing supported hosts retain their current
behavior; this change does not migrate their scheduling mechanisms.

## Upgrade impact

`memu-cola` and `memu-agent` are no longer shipped. Before upgrading, existing
users must use their previous package version to clean up confirmed
integration-owned schedules, retrieval instructions and skills. Preserve user
content, shared memory/configuration and other hosts' tooling. Package upgrades
do not perform this cleanup; the README documents the procedure.
