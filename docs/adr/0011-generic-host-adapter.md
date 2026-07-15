ADR 0011: A Generic Host Adapter — Detect First, Then Bind What Works

- Status: Accepted
- Date: 2026-07-16
- Builds on: ADR 0008 (two seams), ADR 0010 (multi-host adapters, shared CLI builder)
- Scope: how memU integrates with agents that have **no dedicated adapter**. It does not
  change the five dedicated hosts or the pipeline.

## Context

ADR 0010 shipped five dedicated adapters and noted the recipe for a sixth: a `classify`
method, two paths, two markdown files. That recipe assumes someone writes the adapter. The
long tail of agents — new CLIs appear monthly — will mostly never get one, yet many of them
are integrable *today*, because the ecosystem has converged on a handful of session-log
dialects and a handful of instruction-file names.

Two observations make a generic adapter viable:

1. **Session logs cluster into ~5 JSONL dialects.** Payload-wrapped (Codex lineage), typed
   message trees (OpenClaw/pi lineage), typed block records (Claude Code lineage),
   role+message blocks (Cursor lineage), and flat OpenAI-client chat rows. A sniffing
   `classify` that tries these in order covers most JSONL-logging agents without any
   per-agent code.
2. **The two seams degrade independently.** An agent with a readable session log gets
   *memorization* (the record seam) even if we cannot find its instruction file; an agent
   with only an `AGENTS.md`/`CLAUDE.md`/`SOUL.md`-style file gets *retrieval* (the inject
   seam) even if its sessions are unreadable (SQLite, editor state, or absent). Partial
   integration is still integration — but only if the user is told which half they got.

## Decision

One more binary, `memu-agent` (package `memu.hosts.generic`), with the shared verb surface
plus one new verb:

- **`detect` probes before anything binds.** With no argument it surveys `~` for agent
  directories; with a path it probes that directory. For each candidate it answers the two
  questions in order — *is there a session log whose records sniff as a known dialect?*
  (memorization), and if not or additionally, *is there an instruction file to patch?*
  (retrieval) — and prints an explicit per-agent verdict: memorization works / retrieval
  works / both / neither, with the found paths and the exact next command. Directories of
  the five dedicated hosts are redirected to their own binaries. Sessions in containers the
  sniffer cannot read (SQLite and friends) are reported as such — the Hermes precedent, not
  silence.
- **The transcript source sniffs per record.** `GenericTranscriptSource.classify` tries the
  five dialects in order; a record matching none is `OTHER`. This is the same fail-closed
  posture the dedicated adapters take with their hosts' metadata records: the mining jobs
  see only what provably is conversation or tool traffic, so a half-recognized log degrades
  to less input, never to garbage input.
- **Nothing is defaulted that detect must find.** `prepare --session-dir` is *required* (the
  `HostSpec` marks no universal location), and `install-instruction` takes the `--path`
  detect reported. The one machine-specific value the bridging prompt carries is that
  session dir — a deliberate, documented exception to ADR 0009's "nothing machine-specific
  in the prompt", because for an unknown agent there is no `PATH`-stable name to hide it
  behind.
- **Several generic agents share one binary, not one working tree.** The default tree is
  `~/.memu/hosts/agent/`; integrating a second unknown agent means passing
  `--base-dir ~/.memu/hosts/<name>` in that agent's task, keeping ADR 0010's isolation
  guarantee.

## Consequences

Positive:

- Any agent logging a known JSONL dialect integrates with zero new code, and any agent with
  a recognizable instruction file gets retrieval regardless.
- The user always learns *which* seams work and why — the detect report is the contract,
  so a retrieval-only integration is a stated outcome rather than a silent half-failure.
- `detect` doubles as the scouting tool for new dedicated adapters: an unrecognized-dialect
  or SQLite report is exactly the evidence a sixth adapter starts from.

Negative / costs:

- Sniffing is heuristic. A new dialect classifies as `OTHER` (missed memories, safe), and a
  pathological log could mis-bucket records (wrong-track memories, bounded by the dialects'
  mutual exclusivity). The dedicated adapters remain the correctness bar.
- `detect`'s survey reads directory listings across `~/.*` (capped per directory); it is
  read-only but not free, and its skip-list of non-agent dirs needs occasional tending.
- The required `--session-dir` bakes one machine-specific path into the generic bridging
  prompt — accepted, see above.

## Related ADRs

- `docs/adr/0010-multi-host-adapters.md` — the shared CLI builder (`HostSpec`) this reuses,
  extended here with `register_extra` (host-specific subcommands) and required-when-blank
  `session_dir`.
