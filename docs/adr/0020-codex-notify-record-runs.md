# ADR 0020: Codex notify record runs

- Status: Proposed
- Scope: Codex host record triggering and CLI installation prerequisites

## Context

A Desktop installation does not guarantee that a headless Codex CLI is available
in the environment inherited by background processes. Memory preparation and
submission also need backend access independently of the agent's tool sandbox.

## Decision

Codex frontends that execute `notify` invoke `memu-codex hook`, which forwards
any previous notifier and starts a detached `hook-run`. The run owns prepare,
headless job execution, and commit. A per-host lock and a default 30-minute
start cooldown bound overlapping notifications. The agent's session ID is
registered for exclusion from later preparation, and `MEMU_BRIDGING_RUN` prevents
recursive hook runs.

Installation resolves the CLI and executes `--version` with a timeout before
changing notify. Missing or broken commands fail installation. The installer
pins the resolved CLI path; the guide covers CLI installation, current-shell
PATH refresh, Desktop restart, and credential reuse. Version detection is not
an authentication or model-capability test.

The headless Codex command uses approval and sandbox bypass. Its working
directory is the memU staging workspace, but a working directory is not a
security boundary: the child retains the user's filesystem and network access.
This trust requirement must be visible during installation and review.

## Consequences

- The user turn does not wait for memory processing.
- CLI availability is checked before installing a hook that depends on it.
- Desktop notify support must be verified for the actual client version.
- Existing configured credentials are reused; no credentials are copied.
- Other hosts keep their current registration flows.
- Earlier scheduler registrations require separate migration care to avoid two
  record mechanisms running over the same workspace.
