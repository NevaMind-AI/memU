# memU Community Contribution Tasks

[English](tasks.en.md) | [简体中文](tasks.md)

👋 Start with a small task that interests you! Leave a claim in [community issue #790](https://github.com/NevaMind-AI/memU/issues/790), including the task ID, your approach, and the platforms you plan to verify. Wait for a maintainer to confirm the scope before starting.

This page records task background, scope, and acceptance criteria. **Assignments, current progress, and related PRs are tracked in maintainer-confirmed records in #790.** Discuss complex designs first and open a separate RFC issue when needed. Link your PR to #790, include the task ID, and link to the corresponding section of this page.

## 📋 Task Directory

IDs are permanent references: completed tasks remain in the catalog, and their IDs are never reassigned. Stars indicate difficulty; the table is ordered by ID.

| ID | Task / Direction | Type | Difficulty | Availability |
| --- | --- | --- | --- | --- |
| 001 | [Standardize Codex retrieval logs](#task-001) | 🛠️ Engineering | ⭐ | 🙋 Open for claims |
| 002 | [pi hook integration](#task-002) | 🔌 Host integration | ⭐⭐–⭐⭐⭐, split into stages | ✅ Completed: #796 |
| 003 | [Inspect and remove legacy Claude Code system schedules](#task-003) | 🛠️ Engineering | ⭐⭐ per platform | 🙋 Three platforms can be claimed separately |
| 004 | [Check file ownership before removing Codex / Claude skills](#task-004) | 🛠️ Engineering | ⭐⭐ | 🙋 Open for claims |
| 005 | [Clean up query-extract process trees on cancellation and parent exit](#task-005) | 🛠️ Engineering | ⭐⭐⭐ | 💬 Open for claims; discuss the design first |
| 006 | [Standalone memU-docs user documentation site](#task-006) | 📚 Documentation | ⭐⭐ | 📝 Awaiting task breakdown; not open for claims |
| 007 | [Unified checks and hook updates for installed hosts](#task-007) | 🛠️ Engineering | ⭐⭐⭐ | 📝 Awaiting task breakdown; not open for claims |

## 🤝 How to Participate

1. Read the scope, acceptance criteria, and historical discussions, then claim the task in #790. For task 003, specify the platform.
2. Start after a maintainer confirms the scope. Discuss lifecycle, authentication, concurrency, or cross-platform designs first, and split implementation into changes that can be reviewed independently.
3. Submit a PR referencing #790 and the task ID. Explain the change and provide the required tests or runtime verification records. See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development setup and submission requirements.
4. Address review feedback. Discuss scope changes, pauses, or withdrawal under your claim. Maintainers update both language versions of the catalog and #790 after completion and acceptance.

Example claim:

```text
Claim: task-003 / Windows
Approach: Reuse the existing scheduler helper; first check historical task names and actions.
Verification environment: Windows; include the version and permissions used.
```

### ⭐ Difficulty Guide

- **⭐ Beginner**: Clear scope, localized changes, and existing implementations and tests to reference.
- **⭐⭐ Intermediate**: Requires understanding the complete flow, including host integration, error handling, or integration verification.
- **⭐⭐⭐ and above**: Involves lifecycle, authentication, concurrency, or cross-platform behavior. Discuss the design first, then split the implementation.

Coding agents are welcome. Before submitting, read the changes, run the necessary tests, and be ready to explain the key implementation decisions. Clear analysis and verification records help reviews move forward 🌱

<a id="task-001"></a>

## 001 · Standardize Codex Retrieval Logs

Type: 🛠️ Engineering | Difficulty: ⭐ | Open for claims

**Background and scope**

Codex retrieval logs live at `~/.memu/hosts/codex/log/hooks/retrieve/<timestamp>-<pid>.log`. Each file contains an initial record and a final record, with each JSON record written on one line. Claude Code uses `<uuid>.json`, one indented JSON file per retrieval, making queries, matched text, and delivered context easier to read.

Change Codex to write one indented `.json` file per retrieval. Keep the log directory unchanged and preserve existing `.log` files.

**Acceptance criteria**

- Successful retrievals, empty results, and failures each produce a JSON log for that retrieval.
- Preserve existing fields, including the query, extraction status, elapsed time, `retrieve_result`, `additional_context`, `returned_counts`, and `omitted_counts` when the corresponding stage succeeds.
- Concurrent invocations do not overwrite each other's logs. Preserve the hook's existing fault tolerance when log writes fail.
- Update log-related tests without changing retrieval or context delivery behavior.

**References**: [Codex prompt_hook.py](../../src/memu/hosts/codex/prompt_hook.py), [Claude Code prompt_hook.py](../../src/memu/hosts/claude_code/prompt_hook.py). Historical record: [#791](https://github.com/NevaMind-AI/memU/issues/791).

<a id="task-002"></a>

## 002 · pi Hook Integration

Type: 🔌 Host integration | Difficulty: ⭐⭐–⭐⭐⭐, split into stages | ✅ Completed

[#796](https://github.com/NevaMind-AI/memU/pull/796) has merged: the pi extension retrieves asynchronously on user input and starts background memorization after the response and retrieval continuation settle. It reuses the shared workspace lock and 30-minute cooldown. Long inputs use the active provider/model for query extraction with timeout fallback. The CLI provides extension installation, verification, and uninstallation.

Real-host acceptance on Windows covered retrieval delivery, idle continuation, and memory commit/retrieval. Linux/macOS runtime acceptance and the minimum supported pi version remain to be established. Define the scope and acceptance criteria in #790 before continuing that work. Cancellation of shared extraction processes is tracked separately as [task 005](#task-005).

**References**: [pi adapter](../../src/memu/hosts/pi), [ADR 0021](../adr/0021-pi-extension-hooks.md). Historical design discussion: [#792](https://github.com/NevaMind-AI/memU/issues/792).

<a id="task-003"></a>

## 003 · Inspect and Remove Legacy Claude Code System Schedules

Type: 🛠️ Engineering | Difficulty: ⭐⭐ per platform | Platforms can be claimed and submitted in separate PRs

**Background and scope**

Claude Code now uses automatic retrieval and background memorization hooks, but older installations may retain an operating-system scheduled bridge. Provide commands through the Claude Code adapter in `memu-cli` to inspect and remove those registrations, avoiding duplicate memory processing. First establish historical registration methods and current command coverage, then make changes that can be accepted independently for each platform.

| Subtask | Difficulty | Availability |
| --- | --- | --- |
| [003 / Windows](#task-003-windows) | ⭐⭐ | 🙋 Open for claims |
| [003 / Linux](#task-003-linux) | ⭐⭐ | 🙋 Open for claims |
| [003 / macOS](#task-003-macos) | ⭐⭐ | 🙋 Open for claims |

<a id="task-003-windows"></a>

### 🪟 Windows

- Check known and historical task names under `\memU\`; read task actions, execution accounts, and registration locations.
- Verify ordinary user tasks and system-level tasks that require additional permissions to inspect or remove. Report insufficient permissions accurately.
- Reuse the existing Windows scheduler helper, add the Claude Code command entry points, and verify inspection, removal, and readback on a real Windows environment.

<a id="task-003-linux"></a>

### 🐧 Linux

- Check the current user's crontab and system-level cron locations actually used by historical installations.
- Investigate whether memU has systemd timer/service registrations. If present, verify user and system scopes separately. Establish historical registration methods before adding support for the locations that need it.
- Verify inspection, removal, and readback on a real Linux environment, recording permission boundaries.

<a id="task-003-macos"></a>

### 🍎 macOS

- Check user LaunchAgents, system-level LaunchAgents / LaunchDaemons, and crontabs actually used by historical installations.
- Read plist labels, program arguments, and launchd domains to establish whether a registration belongs to the Claude Code memU bridge.
- Verify unloading and configuration removal in the correct domain on a real macOS environment. Report insufficient permissions accurately.

### Current CLI Gaps to Verify

`memu-claude-code schedule uninstall` currently delegates to the older shared
Windows helper. A simulated removal error still returns success and deletes the
local wrapper, prompt, and registration record. Inspection also treats failed
queries as absent tasks. Replace these outcomes with explicit failures and retain
artifacts needed for retry; verify action ownership and absence after deletion.
The Hermes Windows cleanup in PR #802 provides a separate verified path; bringing
Claude Code onto that path and verifying its historical registrations belongs to
this task. Linux/macOS inspection and removal remain platform-specific subtasks.

### Acceptance Criteria for Each Platform

- Provide runnable inspection and targeted removal commands, preferably using the existing `memu-claude-code schedule` integration. Discuss the exact command interface when claiming the task.
- Distinguish unregistered, registered, inspection unavailable, and removal failed. Permission errors must not be reported as “no task” or “removed.”
- Check names, actions, or registration configuration, and remove only registrations confirmed to belong to the Claude Code memU bridge. Preserve registrations of uncertain ownership and report them.
- Inspect again after removal to confirm the result. Repeated removal is safe.
- Preserve schedules belonging to other software and other hosts, existing hooks, shared configuration, and memory data.
- Cover historical names, coexisting registrations, preservation of unrelated tasks, and insufficient permissions in tests. Provide real-platform verification records with the OS version, registration scope, and permissions used.
- Update the relevant CLI help and installation/uninstallation instructions.

**Historical record**: [#793](https://github.com/NevaMind-AI/memU/issues/793).

<a id="task-004"></a>

## 004 · Check File Ownership Before Removing Codex / Claude Skills

Type: 🛠️ Engineering / file protection | Difficulty: ⭐⭐ | Open for claims

**Background and scope**

Both adapters' `remove-instruction` commands share [instruction.py](../../src/memu/hosts/instruction.py). Currently, `remove_skill()` checks only whether `skills/memu-retrieve/SKILL.md` exists, then deletes the entire directory using `shutil.rmtree()`. User edits and additional files are deleted too.

The main `install` workflow already checks skill content, additional files, and links through `installation.check_cleanup()`, but direct `remove-instruction` invocations bypass that check. Review removal of marked blocks from global instruction files separately from deletion of the skill directory.

- Trace every caller of the shared skill deletion function. Reuse existing ownership checks and validate consistently before deletion.
- Preserve user-edited `SKILL.md` files, additional files or subdirectories, and symbolic links, and provide a diagnostic. A path, file presence, or command string alone does not establish ownership of the entire directory.
- Keep complete, confirmed memU-owned skills removable. Repeated invocation and absent targets must be safe, and `--dry-run` must remain read-only.
- Review the order of instruction-block and skill operations so failed checks do not leave partial removals. Preserve unrelated instructions, configuration, and memory.

**Isolated reproduction**

Create the following files in a temporary directory. Use a separate directory for each host; do not reproduce against real user directories:

```text
sandbox/
  rules.md                         # User's own instructions
  skills/memu-retrieve/
    SKILL.md                       # Entirely user-authored content
    notes.txt                      # An additional user file
```

Replace `<sandbox>` with the absolute path to the temporary directory and run each command separately:

```sh
memu-codex remove-instruction --path <sandbox>/rules.md --skills-dir <sandbox>/skills
memu-claude-code remove-instruction --path <sandbox>/rules.md --skills-dir <sandbox>/skills
```

Both commands have been reproduced returning success and preserving `rules.md`, while deleting `memu-retrieve/` and both user files inside it.

**Acceptance criteria**

- Both direct command entry points protect user-edited skills and additional files.
- Cover normal removal with confirmed ownership, absent targets, repeated removal, user edits, additional files/subdirectories, links, and `--dry-run`. State platform permission requirements for link tests.
- Failed protection checks return a clear diagnostic and leave both instruction files and skills unchanged.
- Regression-test migration cleanup in the Codex / Claude installers, and update CLI help or documentation where needed.

**Historical record**: [#799](https://github.com/NevaMind-AI/memU/issues/799).

<a id="task-005"></a>

## 005 · Clean Up Query-Extract Process Trees on Cancellation and Parent Exit

Type: 🛠️ Engineering / subprocess lifecycle | Difficulty: ⭐⭐⭐ | Open for claims; discuss the design first

**Background and scope**

All three hosts share `run_extraction()` in [query_extraction.py](../../src/memu/hosts/query_extraction.py). During normal execution it cleans up the extraction process tree after a 12-second timeout and falls back to retrieval. If the hook's Python parent process is terminated externally, the code responsible for the timeout and cleanup exits too, potentially leaving the extraction child running.

On POSIX, extraction runs in a separate session/process group. On Windows, launcher scripts and their descendants also need cleanup verification. Remaining requests can continue consuming model resources, and hung processes can survive indefinitely.

- Trace startup, cancellation, and termination across the complete process tree. Distinguish normal extraction timeouts, session switches, closure, reload, and abnormal parent exits.
- Design a reusable cleanup mechanism covering the current task's children and descendants. Explain the guarantees for normal and forced termination, and avoid terminating other sessions or user processes.
- Preserve the shared extraction policy, 12-second timeout, failure fallback, and nonblocking input. Cancellation must not start fallback retrieval, deliver stale results, or restart work.
- Outline Windows and POSIX handling in #790 before implementing. Open a separate RFC when needed and split the work into independently reviewable changes.

**Existing Evidence and Open Questions**

- **Confirmed triggering path in pi**: `session_shutdown` in `retrieval-extension.ts` calls `child.kill()` on the retrieval Python process without covering the extraction process started by the shared executor.
- **Successful isolated reproduction on Windows**: a Python parent calls `run_extraction()` to start a mock extractor that writes its PID and sleeps. The extraction child remains alive after the parent is terminated. Test processes were cleaned up afterward.
- **Real Codex / Claude exit behavior remains unverified**: both use the same executor, but their hosts manage hooks. Check whether each host cleans up the entire process tree; shared code alone does not establish that normal switches or exits leave processes behind.

**Acceptance criteria**

- Provide repeatable tests using local mock programs, without model credentials or writes to real memory. Cover direct children and multiple generations of descendants.
- Cover extraction success, extraction timeout, cancellation/parent exit during extraction, and repeated cancellation. Target processes must eventually exit while unrelated processes remain alive.
- Record pi closure, session-switch, and reload verification. Record actual Codex / Claude host behavior and versions separately.
- Provide runtime verification on Windows and POSIX, stating signal, permission, and unsupported forced-termination boundaries. Explicitly record any platform that has not been verified.
- No stale-session result injection after cancellation; existing regression tests for normal timeout fallback continue to pass.

**Historical record**: [#800](https://github.com/NevaMind-AI/memU/issues/800). Related implementation: [#796](https://github.com/NevaMind-AI/memU/pull/796).

<a id="task-006"></a>

## 006 · Standalone memU-docs User Documentation Site

Type: 📚 Documentation | Difficulty: ⭐⭐ | 📝 Awaiting task breakdown; not open for claims

The direction is a standalone user documentation site that makes installation, usage, and troubleshooting guidance easier to find. Discuss the repository, publishing method, content scope, and acceptance criteria in #790 before opening independently deliverable subtasks.

<a id="task-007"></a>

## 007 · Unified Checks and Hook Updates for Installed Hosts

Type: 🛠️ Engineering | Difficulty: ⭐⭐⭐ | 📝 Awaiting task breakdown; not open for claims

The direction is a unified workflow for inspecting installed hosts and updating their hooks. Discuss each host's inspection capabilities, update boundaries, and protection requirements in #790, then define acceptance criteria before opening subtasks for claims.
