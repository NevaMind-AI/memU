# Uninstall memU for Claude Code

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `~/.claude/CLAUDE.md`** — remove the standing retrieval
   instruction (the *inject* seam).
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-codex`,
`memu-cursor`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find the scheduled entry that runs the memU bridging pipeline — a cron entry
(or launchd job, if that is what the user chose at install time) invoking
`claude -p 'Run the memU bridging pipeline. …'` — and delete **only that
entry**. Everything else in the user's crontab is theirs and stays.

- **cron** — `crontab -l` to find the line, then rewrite the crontab without
  it, e.g. `crontab -l | grep -v 'memU bridging pipeline' | crontab -`. If the
  memU line was the only reason a `PATH=` line was added, that line may go too —
  but only if nothing else in the crontab needs it. If nothing at all remains,
  `crontab -r` removes the now-empty crontab cleanly.
- **launchd** — `launchctl bootout gui/$(id -u)/<label>` and delete the plist
  under `~/Library/LaunchAgents`.

### ✅ Verify Part 1

`crontab -l` (and `ls ~/Library/LaunchAgents`, if launchd was used) shows no
memU bridging entry, and everything unrelated is still there.

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

### ✅ Verify Part 2

`cat ~/.claude/CLAUDE.md` — no `memu:begin`/`memu:end` markers remain, and the
user's own content is intact. The session you are working in already loaded
the old file, so the instruction may still be in your own context; a fresh
session is what picks the removal up.

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
- **Remove this host's residue.** `~/.memu/hosts/claude-code/` (job files,
  session cursors, mirrors); `~/.claude/CLAUDE.md` itself **if** Part 2 left it
  empty (it held only memU's block, so the install created it) — a file with
  the user's own content stays, of course; and any allow rules for
  `memu-claude-code` or `~/.memu/` that `~/.claude/settings.json` gained at
  install time.
- **Uninstall the package** — `pip uninstall memu-cli` (or `pipx uninstall
  memu-cli` — match how it was installed) — **unless** another host adapter is
  still integrated on this machine (another host's instruction file still
  carries a memU block, or its bridging task still exists). Then the package
  stays, and the report says which host is still using it.

### ✅ Done

Close the report with the two things the user needs to hear, in this order:

1. **What was kept:** their memory — the store at `MEMU_DB` and
   `~/.memu/config.env` — untouched. A later reinstall picks it up as is.
2. **What was removed:** the bridging schedule, the retrieval instruction,
   this host's working state, and (unless another host still needs it) the
   `memu-cli` package.
