# Uninstall memU for Claude Code

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `~/.claude/CLAUDE.md`** — remove the standing retrieval
   instruction (the *inject* seam).
3. **Decide about the data and the package** — the store is the user's
   accumulated memory; deleting it is their call, never yours.

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
  but only if nothing else in the crontab needs it.
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

## Part 3 — The data, the config, and the package (ask first)

Everything in this part is **opt-in: ask the user, then act.** The safe
default is to keep data.

- **This host's working tree** — `~/.memu/hosts/claude-code/` holds only this
  adapter's run-scoped state (job files, session cursors, mirrors). Safe to
  delete once Parts 1–2 are done.
- **The store and `~/.memu/config.env`** — shared by every host adapter on
  the machine. Delete only if the user says so **and** no other host adapter
  is still integrated. Warn first, in plain words: the store *is* their
  accumulated memory, and deleting it is irreversible.
- **The package** — once no host on this machine uses memU any more:
  `pip uninstall memu-cli` (or `pipx uninstall memu-cli` — match how it was
  installed).
- **Permissions** — if `~/.claude/settings.json` gained allow rules for
  `memu-claude-code` or `~/.memu/` at install time, remove those rules.

### ✅ Done

Report to the user exactly what was removed and what was deliberately kept:
the schedule (gone), the instruction (gone), the store (kept where, or
deleted), the package (kept or uninstalled). If the store was kept, say so
explicitly: reinstalling later picks it right back up — memory survives an
uninstall by design.
