# Uninstall memU (generic `memu-agent`)

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch the instruction file** — remove the standing retrieval
   instruction from wherever `memu-agent install-instruction` put it (the
   *inject* seam).
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

A retrieval-only integration (detect found no recognizable session log, so no
bridging task was ever registered) simply has no Part 1 — skip to Part 2.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-codex`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find where the bridging run was scheduled at install time — the agent's own
scheduler if it has one, otherwise a system cron entry — and delete **that
entry only**. Its prompt is recognizable: the three-step block running
`memu-agent prepare --session-dir …`, the job files, then `memu-agent commit`.
Everything else in the scheduler is the user's and stays; for cron:
`crontab -l | grep -v 'memU bridging pipeline' | crontab -`. If nothing at all
remains, `crontab -r` removes the now-empty crontab cleanly.

### ✅ Verify Part 1

The scheduler (crontab or the agent's own) no longer lists a memU bridging
entry, and everything unrelated is still there.

---

## Part 2 — Remove the retrieval instruction

**Do not hand-edit the block out.** memU owns the text and removes it for you.
From the project root whose `AGENTS.md` was patched (repeat per project if it
was installed into several):

```
memu-agent remove-instruction
```

(or `memu-agent remove-instruction --path <file>` for whatever file
`install-instruction --path` targeted). It deletes memU's marked block and
prints the diff. Everything outside the markers is the user's and survives;
the previous contents are backed up to `<file>.bak` before the rewrite.
`--dry-run` shows the diff without writing. Re-running is a clean no-op — a
file with no block left is already the desired end state.

### ✅ Verify Part 2

Each patched instruction file shows no `memu:begin`/`memu:end` markers, and
the user's own content is intact.

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
- **Remove this host's residue.** `~/.memu/hosts/agent/` (or the `--base-dir`
  chosen at install time, for a named generic agent); and each patched
  instruction file **if** Part 2 left it empty (it held only memU's block, so
  the install created it) — a file with the user's own content stays, of
  course. The agent's own session log belongs to the agent — memU only ever
  read it; leave it alone.
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
