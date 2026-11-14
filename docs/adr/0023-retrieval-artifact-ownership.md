# 0023: Clean Retrieval Artifacts Using Installation Ownership

## Status

Accepted.

Builds on [self-updating templates](0013-self-updating-instruction-templates.md)
and [host memory hooks](0022-host-memory-hooks.md).

## Context

Retrieval has been installed as inline instructions, instruction pointers plus
skills, native hooks and extensions. A host can retain multiple entry points
after a partial migration. Removing its current hook alone does not remove a
previously installed skill. Comparing an installed skill only with today's
embedded template also rejects valid installations after package or server
content changes.

## Decision

Keep instruction ownership in the existing host-specific managed block markers.
On skill installation and refresh, write `.memu-owned.json` beside `SKILL.md`.
It records `binary` and `sha256`, the SHA-256 digest of the installed UTF-8 text
with line endings normalized by Python text reads. These fields are an artifact
contract, not package version identifiers; additional record fields are allowed.

Cleanup verifies directory/file types, rejects links and extra entries, and
requires the record's host and digest to match the installed file. It does not
fetch templates or compare package versions. Changed user content and invalid
records are preserved with an error. A fingerprint is a local ownership/integrity
receipt, not a signature or a security boundary against a user able to edit both
files.

For installations without a record, retain the existing exact packaged-content
check. Arbitrary old or edited content cannot be distinguished safely without
installation evidence; require targeted ownership review rather than inventing
a template-version migration table or trusting a directory name.

Use shared instruction/skill cleanup in `remove-instruction` and in Codex,
Claude Code and pi uninstall flows, even if their current hooks/extensions are
already absent. pi checks both global instruction filenames. Ownership checks
precede current-trigger removal; cleanup errors prevent a successful result.
Memory stores, shared configuration and unrelated instructions/skills remain.

Uninstall guides enumerate scheduler surfaces separately and require confirmed
host actions and readback. Commands do not claim to discover all historical
projects, profiles or OS/native tasks. A shared `memu-cleanup: owned-artifacts`
guide capability marker prevents outdated remote/cache guides from replacing
this cleanup contract; it does not encode a release number.

## Consequences

An unchanged recorded skill remains removable after template updates or package
upgrades, without release-to-release branches. Missing artifacts are no-ops;
partial uninstalls can be retried. A failed receipt write or unknown old content
can still require ownership review. Existing unrecorded installations are not
silently adopted merely because their directory is named `memu-retrieve`.

Custom installation paths still require an explicit inventory. Full uninstall
also requires applicable scheduler checks and unloading existing sessions or
extensions. No whole-machine scan, package removal or memory deletion is implied.
