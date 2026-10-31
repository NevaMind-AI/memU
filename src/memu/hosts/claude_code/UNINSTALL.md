# Uninstall memU for Claude Code

<!-- memu-claude-code-scheduling: retired-v1 -->

Submit hooks and active workers must be removed through the coordinated lifecycle
procedure tracked in [the installation rollout](https://github.com/NevaMind-AI/memU/pull/772).
Do not remove the package or host working state, or report uninstall complete,
while Submit hooks or workers remain active.

## Task identity

- Current task name: `{{task_name}}`
- Former task names: {{former_task_names}}
- Names recognized during migration and removal: {{all_task_names}}

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `~/.claude/CLAUDE.md`** — remove the standing retrieval
   instruction and the `memu-retrieve` skill it points at (the *inject* seam).
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-codex`,
`memu-cursor`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all. Those other
adapters are **out of scope here** — this guide uninstalls the Claude Code host
only. Never touch, unpatch, or run the uninstall for another host: leave its
working tree under `~/.memu/hosts/` (e.g. `~/.memu/hosts/codex/`) and its
instruction file exactly as they are.

---

## Part 1 — Unregister the bridging (record) task

Find legacy registrations with the platform's scheduler tools. Use
{{all_task_names}} as candidate names and confirm that each action runs this
Claude adapter's wrapper or Claude prepare / self-evolve / commit pipeline.
Names or the generic `memU bridging pipeline` phrase alone are insufficient;
leave unrelated and ambiguous entries untouched.

- **Windows:** inspect `Get-ScheduledTask` results, recording each confirmed
  entry's exact task path, task name, action and state. Check historical paths
  as well as the memU namespace.
- **cron:** inspect `crontab -l`, identifying the Claude wrapper at
  `~/.memu/hosts/claude-code/bridge.sh` or the confirmed inline Claude pipeline.
  Preserve unrelated jobs and shared environment lines.
- **launchd:** inspect loaded user jobs with `launchctl` and plist definitions
  under `~/Library/LaunchAgents`, recording the confirmed labels and paths.

Disable or pause confirmed registrations to prevent new launches, then wait for
running workers and their descendants to finish naturally. Do not kill workers.
If inventory, ownership or running state cannot be established, stop and report
the unresolved migration.

Once idle, remove only confirmed registrations using the platform's scheduler
tools, then query again. Remove confirmed generated wrappers and prompt files
only after the registrations are gone; preserve pending jobs, results, cursors
and logs during migration.

### ✅ Verify Part 1

Every confirmed Claude registration is absent, its old workers have exited, and
unrelated registrations remain. An unavailable inventory is not a successful
cleanup. Continue only after these checks pass.

---

## Part 2 — Remove the retrieval instruction

**Do not hand-edit the block out.** memU owns the text and removes it for you:

```
memu-claude-code remove-instruction
```

It deletes memU's marked block from `~/.claude/CLAUDE.md` and prints the diff.
Everything outside the markers is the user's and survives; the previous
contents are backed up to `~/.claude/CLAUDE.md.bak` before the rewrite.
`--dry-run` shows the diff without writing. Re-running is a clean no-op — a
file with no block left is already the desired end state.

On Claude Code the block is a **pointer** to memU's `memu-retrieve` skill,
installed at `~/.claude/skills/memu-retrieve/`. The same command takes that
skill out too — the pointer first, then the skill, so no live instruction is
ever left aiming at a deleted skill. The directory is memU's own (the install
wrote it whole, so it goes whole); a same-named directory without memU's
`SKILL.md` is left alone, as are the user's or Claude Code's other entries in
`~/.claude/skills/`. So there is nothing to remove by hand.

### ✅ Verify Part 2

`cat ~/.claude/CLAUDE.md` — no `memu:begin`/`memu:end` markers remain, and the
user's own content is intact; `~/.claude/skills/memu-retrieve` no longer
exists. The session you are working in already loaded the old file, so the
instruction may still be in your own context; a fresh session is what picks
the removal up.

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
  `~/.memu/hosts/claude-code/.session_manifest.claude-code.json` records
  which session turns have already been mined *into that store*. Store
  kept (the default)? Keep the cursor — deleting it loses no memory, but the
  next install re-mines every old session for nothing. Store deleted at the
  user's request? Delete the cursor with it — a surviving cursor over an empty
  store marks history as already mined, and it would never be mined again.
- **Remove this host's residue.** Everything else under
  `~/.memu/hosts/claude-code/` — job files and mirrors, sparing the session
  cursor above; `~/.claude/CLAUDE.md` itself **if** Part 2 left it
  empty (it held only memU's block, so the install created it) — a file with
  the user's own content stays, of course; and any allow rules for
  `memu-claude-code` or `~/.memu/` that `~/.claude/settings.json` gained at
  install time.
- **Tell memU the uninstall happened — before the package can go.** The seams
  are gone and the residue is removed; do this *before* the bullet below can
  take `memu-claude-code` off this machine:

  ```
  memu-claude-code report uninstall
  ```

  Unlike every other memU event, this one is delivered on the spot instead of
  waiting for a later bridging run — because the next bullet may remove the very
  binary that would have delivered it. Run it here even when the package is
  staying (another host still needs it): the position is what makes it reliable,
  not the outcome below. Best-effort as always — if it fails, ignore it.
- **If the uninstall failed, or you are stopping early**, report that instead —
  from the same place, while the binary still exists:

  ```
  memu-claude-code report error --stage uninstall --detail "<a full account of what went wrong>"
  ```

  **Be generous with `--detail`** — it is all a memU engineer gets to work out
  what happened here. A paragraph or two of plain language: what would not come
  out, what you ran, what happened instead, what you tried, and what you think
  the cause is. **Detailed, not a transcript**, though: do not paste the
  traceback or raw command output, which memU reports on its own, and never
  include a credential, an absolute path (`/Users/…`, `C:\Users\…`), a store
  DSN or an endpoint URL, or memory or transcript text — describe those in words
  instead. If `pip uninstall` itself is what failed, `memu-claude-code` is usually still
  on `PATH` — try the report once; if the command is gone too, there is nothing
  to report with, and that is fine.
- **Uninstall the package — only if this is the last memU host.** `memu-cli` is
  shared by every host adapter, so uninstall it (`pip uninstall memu-cli`, or
  `pipx uninstall memu-cli` — match how it was installed) **only once no other
  host is still integrated on this machine.** To check, list `~/.memu/hosts/`:
  any directory there *other than* this host's own `~/.memu/hosts/claude-code/`
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
2. **What was removed:** the bridging schedule, the retrieval instruction,
   this host's working state, and (unless another host still needs it) the
   `memu-cli` package.
