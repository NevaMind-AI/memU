# Uninstall memU for Codex

<!-- memu-codex-record: submit-v1 -->

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

This guide removes both current and known historical Codex memU integrations,
including partial upgrades. Check every subsection: finding a current hook does
not mean old tasks or instructions are gone. An absent entry is a normal no-op;
do not create or reinstall anything in order to uninstall it. Preserve unrelated
hosts, hooks, tasks and user instructions. Report unresolved ownership separately
and keep the package while any confirmed entry still needs its executable.

Uninstalling has three parts:

1. **Remove the memU notify entry and confirmed old schedules** — prevent new
   record runs, then let existing agents finish (the *record* seam).
2. **Remove both Submit hooks and their trust entries** — clean up the
   `UserPromptSubmit` command and any old memU skill/instruction (the *inject* seam).
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-cursor`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all. Those other
adapters are **out of scope here** — this guide uninstalls the Codex host only.
Never touch, unpatch, or run the uninstall for another host: leave its working
tree under `~/.memu/hosts/` (e.g. `~/.memu/hosts/claude-code/`) and its
instruction file exactly as they are.

---

## Part 1 — Remove record triggers and wait for running agents

### 1.1 Current entry — notify

Inspect the parsed notify chain. If it contains no memU callback, continue to
historical schedules without modifying the user's notifier.

Save the current notify configuration locally before changing it. For a direct
memU notify command, use `memu-codex remove-hook`; repeating it is a no-op and
unrelated notify commands are preserved. Read the configuration back.

The current remover does not unwrap Desktop's `turn-ended --previous-notify`
chain. If that wrapper contains memU, preserve the outer Desktop command and
remove only the confirmed memU callback through the wrapper's supported
configuration path. Restore a saved predecessor only after verifying that the
backup belongs to this chain. Never overwrite an unrelated or newer notifier
from a stale backup. If this cannot be done safely, stop the uninstall and
report the remaining callback; do not remove its executable.

### 1.2 Historical entries — scheduled bridging tasks

Inspect Windows Task Scheduler in all folders and Codex's native task surface.
Candidate names are {{all_task_names}}, but actions, wrapper contents or the full
prepare / self-evolve / commit prompt must confirm **Codex** ownership. Leave
other hosts and ambiguous registrations untouched. Save restorable definitions
and original states locally before disabling/removing confirmed tasks, following
the migration section of `memu-codex docs install`. Do not invoke another host's
schedule helper. No confirmed task is a no-op; multiple confirmed registrations
must each be removed, even if a current notify callback was also found.

### 1.3 Wait for affected runs before cleanup

Disable future triggers first. Removing a registration does not stop a running
agent. Do not terminate it; wait for all affected runs and descendants to finish
naturally before deleting registrations, working files or the package. If a run
is still active or ownership is unresolved, leave uninstall pending. Keep logs,
recovery definitions, original wrappers, backend config, memories and cursors.

### ✅ Verify Part 1

The parsed notify chain no longer invokes memU, confirmed old registrations are
absent from both scheduler surfaces, and affected agents have finished. Other
notifiers and hosts remain intact. Repeating the removal is a no-op.

---

## Part 2 — Remove the Submit hooks, trust and old instruction

### 2.1 Current entry — UserPromptSubmit hook and trust

Inspect `~/.codex/hooks.json` and relevant trust state if they exist. A missing
file or absent memU hook is a normal no-op; continue to the historical instruction
check. Remove a leftover approval only if its ownership can still be confirmed.

Back up `~/.codex/hooks.json` and the relevant Codex hook trust state locally.
Identify the `UserPromptSubmit` command by its resolved memu-codex executable
and `prompt-hook` or `memorize-hook` argument. Remove both confirmed entries, preserving other
hooks and events. Remove its corresponding approval using the installed Codex
version's hook trust facilities; current Windows versions persist the fingerprint
in `~/.codex/config.toml` under `hooks.state` as `trusted_hash`.

Trust keys include the hooks file path and matcher/command indices. If removal
changes other hooks' indices, verify their approvals through Codex rather than
copying or deleting unrelated fingerprints. Repeating removal when the memU
entry is absent must preserve all unrelated configuration.

Automatic hook/trust removal is not yet integrated in memu-cli. If safe removal
cannot be completed with the installed Codex version, report uninstall as pending
and retain the executable. Do not leave a registered hook pointing at a removed
package.

### 2.2 Historical entries — AGENTS instruction and retrieve skill

Check these independently of the current hook; they can remain after a partial
upgrade. Inspect `~/.codex/AGENTS.md` for memU's marked block and
`~/.codex/skills/memu-retrieve/SKILL.md` for the owned retrieval procedure.
Confirm ownership before removal: the shared command treats an existing
SKILL.md in that named directory as its marker. Preserve ambiguous or user-owned
content and report it for review.

Preview the existing cleanup command and review its diff:

```text
memu-codex remove-instruction --dry-run
```

Then remove the confirmed old instruction and skill:

```text
memu-codex remove-instruction
```

It deletes memU's marked block from `~/.codex/AGENTS.md` and prints the diff.
Everything outside the markers is the user's and survives; the previous
contents are backed up to `~/.codex/AGENTS.md.bak` before the rewrite.
`--dry-run` shows the diff without writing. Re-running is a clean no-op — a
file with no block left is already the desired end state.

On Codex the block is a **pointer** to memU's `memu-retrieve` skill, installed
at `~/.codex/skills/memu-retrieve/`. The same command takes that skill out too
— the pointer first, then the skill, so no live instruction is ever left aiming
at a deleted skill. The directory is memU's own (the install wrote it whole, so
it goes whole); a same-named directory without memU's `SKILL.md` is left alone,
as are the user's or Codex's other entries in `~/.codex/skills/`. So there is
nothing to remove by hand. If both old entries are absent, this step is already
complete. Never delete the whole skills directory or memU's distribution/install
SKILL.md. Custom skill locations or unmarked references require confirmed
ownership and targeted cleanup; do not remove unrelated user text.

### ✅ Verify Part 2

Read back `hooks.json` and the hook trust state: the confirmed memU prompt-hook and memorize-hook
and their approvals are gone, and unrelated hooks remain configured and trusted.
`~/.codex/AGENTS.md` has no memU instruction markers, its user content is intact,
and the owned `~/.codex/skills/memu-retrieve` skill is gone. A fresh Codex session
must no longer attempt to run memU retrieval. The session you are working in may
still carry the old instruction in its context.

---

## Part 3 — The data, the config, and the package (defaults, then report)

No questions to ask here. Apply the defaults below, and make sure the final
report tells the user plainly what they got: **memory kept, tooling removed.**
Only one thing overrides a default: the user's own explicit words.

- **Keep the store and `~/.memu/config.env`.** Always. The store *is* the
  user's accumulated memory, and it survives an uninstall by design —
  reinstalling later picks it right back up. Delete it only if the user
  explicitly asked to erase their memory as part of this uninstall, and warn
  first, in plain words, that it is irreversible.
- **The session cursor lives and dies with the store.** The `.session_manifest*`
  files under `~/.memu/hosts/codex/`
  record which session turns have already been mined *into that store*. Store
  kept (the default)? Keep the cursor — deleting it loses no memory, but the
  next install re-mines every old session for nothing. Store deleted at the
  user's request? Delete the cursor with it — a surviving cursor over an empty
  store marks history as already mined, and it would never be mined again.
- **Remove this host's residue.** Codex's run-scoped working tree is
  `~/.memu/hosts/codex/`: the `jobs/`, `sessions/`, `memory/`, and `skill/`
  directories and `resources.md` — but **not** logs, recovery definitions,
  original scheduler wrappers or the `.session_manifest*` cursor
  files there (see above), unless the store is going too. The shared
  `~/.memu/config.env` and the store file sit at the `~/.memu/` root, outside
  this tree, so removing the tree never touches them. Also
  `~/.codex/AGENTS.md` itself **if** Part 2
  left it empty (it held only memU's block, so the install created it) — a
  file with the user's own content stays, of course.
- **Tell memU the uninstall happened — before the package can go.** The seams
  are gone and the residue is removed; do this *before* the bullet below can
  take `memu-codex` off this machine:

  ```
  memu-codex report uninstall
  ```

  Unlike every other memU event, this one is delivered on the spot instead of
  waiting for a later bridging run — because the next bullet may remove the very
  binary that would have delivered it. Run it here even when the package is
  staying (another host still needs it): the position is what makes it reliable,
  not the outcome below. Best-effort as always — if it fails, ignore it.
- **If the uninstall failed, or you are stopping early**, report that instead —
  from the same place, while the binary still exists:

  ```
  memu-codex report error --stage uninstall --detail "<a full account of what went wrong>"
  ```

  **Be generous with `--detail`** — it is all a memU engineer gets to work out
  what happened here. A paragraph or two of plain language: what would not come
  out, what you ran, what happened instead, what you tried, and what you think
  the cause is. **Detailed, not a transcript**, though: do not paste the
  traceback or raw command output, which memU reports on its own, and never
  include a credential, an absolute path (`/Users/…`, `C:\Users\…`), a store
  DSN or an endpoint URL, or memory or transcript text — describe those in words
  instead. If `pip uninstall` itself is what failed, `memu-codex` is usually still
  on `PATH` — try the report once; if the command is gone too, there is nothing
  to report with, and that is fine.
- **Uninstall the package — only if this is the last memU host.** `memu-cli` is
  shared by every host adapter, so uninstall it (`pip uninstall memu-cli`, or
  `pipx uninstall memu-cli` — match how it was installed) **only once no other
  host is still integrated on this machine.** To check, list `~/.memu/hosts/`:
  any directory there *other than* this host's own `~/.memu/hosts/codex/`
  (which may survive, holding just the kept session cursor) is another live
  host — confirm it by its instruction file still carrying a memU block, or its
  bridging task still existing. If any other host remains, leave `memu-cli`
  installed and name the surviving host(s) in the report.
- **The shared event spool goes with the package, and only with it.** The
  report above empties `~/.memu/events.jsonl` on delivery, but a machine that
  was offline leaves it — or one of its sidecars (`events.jsonl.*.sending`,
  `events.errors`, `events.dropped`) — behind. Remove them **only** if you
  removed `memu-cli`: the spool is
  machine-scoped and shared with every other host, so deleting it while one
  remains throws away events that host has not delivered yet.

### ✅ Done

Close the report with the two things the user needs to hear, in this order:

1. **What was kept:** their memory — the store at `MEMU_DB`,
   `~/.memu/config.env`, and the session cursor — untouched. A later reinstall
   picks it up as is and resumes mining right where it left off.
2. **What was removed:** list current notify/hook/trust entries and historical
   schedules/instructions/skills separately, noting entries already absent and
   any unresolved remnants. Also report this host's working state and whether
   the shared `memu-cli` package was removed or retained for another host.
