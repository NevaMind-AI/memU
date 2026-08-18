# Uninstall memU for WorkBuddy

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled automation first, so
   nothing fires mid-teardown (the *record* seam).
2. **Unpatch `~/.workbuddy/SOUL.md`** — remove the standing retrieval instruction
   (the *inject* seam), including any block left in the legacy `MEMORY.md` target.
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-codex`,
`memu-claude-code`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all. Those other
adapters are **out of scope here** — this guide uninstalls the WorkBuddy host
only. Never touch, unpatch, or run the uninstall for another host: leave its
working tree under `~/.memu/hosts/` (e.g. `~/.memu/hosts/codex/`) and its
instruction file exactly as they are.

---

## Part 1 — Unregister the bridging (record) task

Find the WorkBuddy automation whose task text carries a recognized name from
{{all_task_names}} and the "memU bridging pipeline" prompt, then delete only its
exact automation ID through WorkBuddy's automation management. The name alone
is never enough to delete.

### ✅ Verify Part 1

The automation no longer appears in WorkBuddy's automation list.

---

## Part 2 — Remove the retrieval instruction

**Do not hand-edit the block out.** memU owns the text and removes it for you:

```
memu-workbuddy remove-instruction
```

It deletes memU's marked block from `~/.workbuddy/SOUL.md` and also checks the
former `~/.workbuddy/MEMORY.md` target so an older install is removed cleanly.
Everything outside the markers is the user's and survives; each changed file is
backed up to its adjacent `.bak` path before the rewrite. `--dry-run` shows both
diffs without writing. Re-running is a clean no-op — files with no block left are
already the desired end state.

### ✅ Verify Part 2

Check both `cat ~/.workbuddy/SOUL.md` and `cat ~/.workbuddy/MEMORY.md`: no
`memu:begin`/`memu:end` markers remain, and the user's own content is intact. The
session you are working in already loaded the old file, so the instruction may
still be in your own context; a fresh session is what picks the removal up.

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
- **The session cursor lives and dies with the store.**
  `~/.memu/hosts/workbuddy/.session_manifest.workbuddy.json` records which
  session turns have already been mined *into that store*. Store kept (the
  default)? Keep the cursor — deleting it loses no memory, but the next install
  re-mines every old session for nothing. Store deleted at the user's request?
  Delete the cursor with it — a surviving cursor over an empty store marks
  history as already mined, and it would never be mined again.
- **Remove this host's residue.** Everything else under
  `~/.memu/hosts/workbuddy/` — job files and mirrors, sparing the session
  cursor above; `~/.workbuddy/SOUL.md` itself **if** Part 2 left it empty
  (it held only memU's block, so the install created it) — a file with the
  user's own content stays, of course.
- **Tell memU the uninstall happened — before the package can go.** The seams
  are gone and the residue is removed; do this *before* the bullet below can
  take `memu-workbuddy` off this machine:

  ```
  memu-workbuddy report uninstall
  ```

  Unlike every other memU event, this one is delivered on the spot instead of
  waiting for a later bridging run — because the next bullet may remove the very
  binary that would have delivered it. Run it here even when the package is
  staying (another host still needs it): the position is what makes it reliable,
  not the outcome below. Best-effort as always — if it fails, ignore it.
- **If the uninstall failed, or you are stopping early**, report that instead —
  from the same place, while the binary still exists:

  ```
  memu-workbuddy report error --stage uninstall --detail "<a full account of what went wrong>"
  ```

  **Be generous with `--detail`** — it is all a memU engineer gets to work out
  what happened here. A paragraph or two of plain language: what would not come
  out, what you ran, what happened instead, what you tried, and what you think
  the cause is. **Detailed, not a transcript**, though: do not paste the
  traceback or raw command output, which memU reports on its own, and never
  include a credential, an absolute path (`/Users/…`, `C:\Users\…`), a store
  DSN or an endpoint URL, or memory or transcript text — describe those in words
  instead. If `pip uninstall` itself is what failed, `memu-workbuddy` is usually still
  on `PATH` — try the report once; if the command is gone too, there is nothing
  to report with, and that is fine.
- **Uninstall the package — only if this is the last memU host.** `memu-cli` is
  shared by every host adapter, so uninstall it (`pip uninstall memu-cli`, or
  `pipx uninstall memu-cli` — match how it was installed) **only once no other
  host is still integrated on this machine.** To check, list `~/.memu/hosts/`:
  any directory there *other than* this host's own `~/.memu/hosts/workbuddy/`
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
2. **What was removed:** the bridging automation, the retrieval instruction,
   this host's working state, and (unless another host still needs it) the
   `memu-cli` package.
