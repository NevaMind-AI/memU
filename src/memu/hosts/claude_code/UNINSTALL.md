# Uninstall memU for Claude Code

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

Find the scheduled entry that runs the memU bridging pipeline — a cron entry
(or launchd job, if that is what the user chose at install time) invoking
`~/.memu/hosts/claude-code/bridge.sh` (or, on installs predating the prompt-file
layout, inlining `claude -p 'Run the memU bridging pipeline. …'` directly) —
and delete **only that entry**. Everything else in the user's crontab is theirs
and stays.

- **cron** — `crontab -l` to find the line, then rewrite the crontab without
  it, e.g.
  `crontab -l | grep -vE 'hosts/claude-code/bridge\.sh|memU bridging pipeline' | crontab -`.
  If the memU line was the only reason a `PATH=` line was added, that line may
  go too — but only if nothing else in the crontab needs it. If nothing at all
  remains, `crontab -r` removes the now-empty crontab cleanly. The `bridge.sh`,
  `bridge-prompt.txt`, and `bridge.log` files live under
  `~/.memu/hosts/claude-code/` and go with the host residue in Part 3.
- **launchd** — `launchctl bootout gui/$(id -u)/<label>` and delete the plist
  under `~/Library/LaunchAgents`.
- **Windows (Task Scheduler)** — the task was registered by the helper, so remove
  it the same way; it also deletes the generated wrapper and prompt file:

  ```
  memu-claude-code schedule uninstall
  ```

### ✅ Verify Part 1

`crontab -l` (and `ls ~/Library/LaunchAgents`, if launchd was used) shows no
memU bridging entry, and everything unrelated is still there. On Windows,
`memu-claude-code schedule status` reports not-registered (equivalently,
`Get-ScheduledTask -TaskPath '\memU\'` finds nothing).

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
- **Uninstall the package — only if this is the last memU host.** `memu-cli` is
  shared by every host adapter, so uninstall it (`pip uninstall memu-cli`, or
  `pipx uninstall memu-cli` — match how it was installed) **only once no other
  host is still integrated on this machine.** To check, list `~/.memu/hosts/`:
  any directory there *other than* this host's own `~/.memu/hosts/claude-code/`
  (which may survive, holding just the kept session cursor) is another live
  host — confirm it by its instruction file still carrying a memU block, or its
  bridging task still existing. If any other host remains, leave `memu-cli`
  installed and name the surviving host(s) in the report.

### ✅ Done

Close the report with the two things the user needs to hear, in this order:

1. **What was kept:** their memory — the store at `MEMU_DB`,
   `~/.memu/config.env`, and the session cursor — untouched. A later reinstall
   picks it up as is and resumes mining right where it left off.
2. **What was removed:** the bridging schedule, the retrieval instruction,
   this host's working state, and (unless another host still needs it) the
   `memu-cli` package.
