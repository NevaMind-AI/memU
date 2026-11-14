# 0024: Remove Cola and Generic Host Adapters

## Status

Accepted. Supersedes [ADR 0011](0011-generic-host-adapter.md) for current host support.

## Context

Maintaining adapters requires validating host lifecycle events, session identity,
retrieval delivery and cleanup. The project is focusing new host integrations on
explicit lifecycle hooks, building on [ADR 0022](0022-host-memory-hooks.md).
The Cola and generic implementations have no committed maintenance capacity for
that direction. Probing an unknown host's files cannot establish this contract.

## Decision

Remove the Cola and generic adapter packages, their CLI registrations and their
specific tests. Supported hosts remain explicitly listed in the installation
routing skill; an unlisted host stops before package installation.

Future hosts can be introduced through community PRs with an explicit lifecycle
integration, tests and documentation. Existing supported adapters retain their
current behavior; this decision does not migrate their scheduling mechanisms.

## Consequences

This is a breaking CLI change: `memu-cola` and `memu-agent` are no longer shipped.
Existing users must clean up their integrations using the previous package
version before upgrading. Cleanup covers confirmed integration-owned schedules,
retrieval instructions and skills while preserving user content, shared memory,
configuration and other hosts. Package upgrades do not perform this cleanup.
The README documents the upgrade procedure.

Historical ADRs and changelog entries remain as records of earlier designs.
