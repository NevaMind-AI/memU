# Claude hook installation rollout

Implementation and acceptance checklist for the final `claude-dev` installation
slice. This is a development plan, not an installation guide. Follow the existing
[acceptance plan](https://github.com/MrXnneHang/xnnehang.top/issues/218) for the
full evidence requirements.

## Current baseline

- `prompt-hook` retrieves on `UserPromptSubmit` and returns bounded context.
  Native `async: true` registration lets Claude proceed before retrieval finishes;
  [retrieval configuration](retrieval.md#claude-code-prompt-hook) documents delivery
  at later model-request boundaries and the internal timeout.
- `memorize-hook --agent <executable>` starts the detached prepare → evolve →
  commit worker with shared admission and cooldown.
- The packaged INSTALL and UNINSTALL guides still describe scheduled bridging
  and skill-based retrieval. Hook installation and migration remain unfinished.
- CLI and Desktop Code have delivered dual-handler probe context. Controlled
  Windows CLI 2.1.312 and Desktop Code runtime 2.1.234 checks also verified native
  asynchronous retrieval within one user turn: the hook completed during a tool
  call, and the model reproduced a random marker after the tool returned. The
  marker was absent from the user prompt and tool output. Retrieval data was
  synthetic; real backend behavior, installation acceptance, and permission-mode
  coverage remain separate checks.

## Installation and lifecycle changes

- [ ] Rewrite Claude INSTALL around backend verification, standalone Claude
  readiness, and two independent Submit handlers. Reuse working configuration
  and authentication; honor the requested package manager and package source.
- [ ] Provide repeatable registration, inspection, and targeted removal of the
  owned handlers. Verify actual executable paths and hook loading; preserve
  third-party hooks, permissions, and unrelated settings.
- [ ] Define supported Claude versions and command representation using tested
  behavior, including Windows paths with spaces and special characters.
- [ ] Correct the authentication instructions: distinguish existing CLI login,
  a persisted OAuth token, and an API key. Verify the background environment;
  do not describe `setup-token` as automatically saving a login.
- [ ] Identify owned legacy schedules and active workers. Coordinate handoff
  without overlapping old and new pipelines or killing existing work. Verify
  replacement registration before removing the old integration.
- [ ] Remove the owned CLAUDE.md retrieval block and retrieval skill after hook
  verification. Check instruction refresh cannot restore the retired flow.
- [ ] Retire the packaged BRIDGING_TASK guide and reject incompatible remote or
  cached lifecycle guides. Keep old scheduler support available where needed
  for targeted migration and removal.
- [ ] Update UNINSTALL to remove hooks and owned legacy registrations, account
  for active workers, and preserve shared configuration, memory, cursors,
  self-session records, and recoverable pending work.
- [ ] Synchronize CLI help and user documentation with the final installation
  entry point. Add an ADR for finalized architecture decisions if needed.

## Permission and product acceptance

Record actual client/runtime versions, OS, permission mode, package source,
implementation commit, and observed outcome for every real installation run.
Do not infer permissions from an installation command succeeding.

| Scenario | Required evidence | Status |
| --- | --- | --- |
| Normal interactive approval | Prompts are actionable; approval resumes the same installation safely | Pending |
| Auto mode | Approval or review rejection is explicit; a supported continuation remains available | Pending |
| Plan mode | Explain blocked installation and the next supported action; do not report success | Pending |
| Bypass mode, where available | Verify installation and worker behavior separately; restore the user's preferred mode afterward | Pending |
| Existing unrelated hooks/settings | Install and removal preserve them | Pending |
| Repeated install | Exactly one copy of each memU handler; no unnecessary reconfiguration | Pending |
| Legacy migration | Owned schedules/skill retire safely; progress and pending work survive | Pending |
| Uninstall and reinstall | Owned triggers disappear and return cleanly; stored memory remains | Pending |

Never automatically disable installation review or broaden permissions to make
a blocked run pass. Follow the actual client's supported approval and terminal
installation paths. Codex's installation structure is a reference; its Full
access gate is not a Claude permission contract.

## Runtime verification after registration

Installation success requires verified configuration, hook loading, and applicable
legacy cleanup. Report runtime evidence separately; do not wait for an entire
background pass to announce registration success.

- [ ] Real CLI and Desktop local Code turns proceed without waiting for the
  asynchronous retrieval handler and later receive its context without an
  agent-initiated retrieve command, including successful empty results. Record
  when context arrived instead of assuming it influenced the initial answer.
- [ ] A real background pass commits an authorized test memory that can then be
  retrieved; no-op success is tested separately.
- [ ] Busy/cooldown skips, recursion suppression, and next-pass exclusion of the
  background session and its subagents work with real Claude execution.
- [ ] Agent/commit failure preserves formal cursor and recoverable work; retry
  completes without silently losing input. Check worker lifetime after frontend exit.
- [ ] Automated regressions and quality checks pass, including shared Codex paths.

Cowork remains an input source consumed by a later Code Submit. This slice does
not promise direct Cowork Submit triggering, Cowork answer-time retrieval, or
coverage of Desktop ordinary Chat. Record untested platforms and versions explicitly.
