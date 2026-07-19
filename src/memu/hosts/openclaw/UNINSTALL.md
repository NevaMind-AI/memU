# Uninstall memU for OpenClaw

> **Audience: the agent.** A user has pointed you at this file ("follow this
> guide to uninstall memU"). Work top to bottom. Each part ends with a
> **verify** gate — do not proceed until the current one passes.

Uninstalling is the install run in reverse, and it is three parts:

1. **Unregister the bridging task** — stop the scheduled job first, so nothing
   fires mid-teardown (the *record* seam).
2. **Unpatch `~/.openclaw/workspace/AGENTS.md`** — remove the standing
   retrieval instruction (the *inject* seam).
3. **Apply the data-and-package defaults** — the user's memory is kept, the
   tooling is removed — and close by reporting both.

**One store, many hosts.** `~/.memu/config.env` and the store it names may be
shared by other memU host adapters on this machine (`memu-claude-code`,
`memu-codex`, …). Removing *this* host's seams never requires touching the
shared store; Part 3 spells out when touching it is safe at all.

---

## Part 1 — Unregister the bridging (record) task

Find the OpenClaw cron job that runs the memU bridging pipeline — it was
created at install time through OpenClaw's native scheduler with the
three-step prepare / self-evolve / commit prompt — and delete **that job
only**, through the same scheduler surface. Any other cron jobs the user has
are theirs and stay.

### ✅ Verify Part 1

OpenClaw's cron job list no longer shows a memU bridging job.

---

## Part 2 — Remove the retrieval instruction

**Do not hand-edit the block out.** memU owns the text and removes it for you:

```
memu-openclaw remove-instruction
```

It deletes memU's marked block from `~/.openclaw/workspace/AGENTS.md` and
prints the diff. Everything outside the markers is the user's and survives;
the previous contents are backed up to
`~/.openclaw/workspace/AGENTS.md.bak` before the rewrite. `--dry-run` shows
the diff without writing. Re-running is a clean no-op — a file with no block
left is already the desired end state.

### ✅ Verify Part 2

`cat ~/.openclaw/workspace/AGENTS.md` — no `memu:begin`/`memu:end` markers
remain, and the user's own content is intact. A session already running loaded
the old file; a fresh session is what picks the removal up.

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
  `~/.memu/hosts/openclaw/.session_manifest.openclaw.json` records which
  session turns have already been mined *into that store*. Store
  kept (the default)? Keep the cursor — deleting it loses no memory, but the
  next install re-mines every old session for nothing. Store deleted at the
  user's request? Delete the cursor with it — a surviving cursor over an empty
  store marks history as already mined, and it would never be mined again.
- **Remove this host's residue.** Everything else under
  `~/.memu/hosts/openclaw/` — job files and mirrors, sparing the session
  cursor above; and `~/.openclaw/workspace/AGENTS.md` itself
  **if** Part 2 left it empty (it held only memU's block, so the install
  created it) — a file with the user's own content stays, of course.
- **Uninstall the package** — `pip uninstall memu-cli` (or `pipx uninstall
  memu-cli` — match how it was installed) — **unless** another host adapter is
  still integrated on this machine (another host's instruction file still
  carries a memU block, or its bridging task still exists). Then the package
  stays, and the report says which host is still using it.

### ✅ Done

Close the report with the two things the user needs to hear, in this order:

1. **What was kept:** their memory — the store at `MEMU_DB`,
   `~/.memu/config.env`, and the session cursor — untouched. A later reinstall
   picks it up as is and resumes mining right where it left off.
2. **What was removed:** the bridging schedule, the retrieval instruction,
   this host's working state, and (unless another host still needs it) the
   `memu-cli` package.
