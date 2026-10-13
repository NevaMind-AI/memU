# 0020: SDK-owned, version-scoped instruction distribution on R2

- Status: Accepted
- Date: 2026-10-13
- Supersedes ADR 0013's unversioned URL/cache namespace and release-copy assumption.

## Context

An old website copy can be syntactically valid but incompatible with a newly
installed SDK. Server-first resolution makes manual synchronization a runtime
risk. Placing every historical release in the marketing website repository also
couples two unrelated deployment processes. We still need compatible wording
corrections without requiring users to upgrade the SDK.

## Decision

The SDK defaults to `/sdk/<installed-distribution-version>/instructions/...` and
`/sdk/<installed-distribution-version>/docs/<host>/...`. The version comes from
`str(packaging.version.Version(importlib.metadata.version("memu-cli")))`.
Explicit normalization is necessary: wheel METADATA can retain the original
version spelling even when the wheel filename is normalized.
Job and doc caches use the same version namespace. Existing explicit base URL
overrides remain exact base URLs, including the empty-string offline switch;
operators using overrides are responsible for pointing them at compatible files.

Release CI exports raw templates and packaged host guides from the actual wheel,
validates the placeholder contracts, and generates a content-hash manifest. A
private R2 bucket stores revision snapshots. A small read-only Worker serves only
published paths through a Cloudflare route on `/sdk/*`. The website repository
continues to own its installation entry point `/SKILL.md`.

The publisher uploads a complete snapshot before replacing `current.json` for
that SDK version. Normal release publication refuses to replace different
content; a separate manual workflow permits a reviewed compatible correction.
Old snapshots remain available for rollback. Publish jobs are serialized.
Normal PyPI releases reject duplicate versions so a skipped wheel upload cannot
lead to publishing assets for a different package with the same version. Public
responses bypass caching and the workflow verifies the active manifest and every
file hash after upload. A failed upload or missing version retains the existing
SDK fallback behavior. Deployment is opt-in via repository configuration.

## Consequences

No independent server or upload service is required. No generated release files
are committed to the website or SDK repository, and no cross-repository PR is
needed. R2 and the Worker need one-time configuration; Worker code deployment is
separate from object publication. Object hashes protect publication integrity,
not authenticity against a writer with bucket credentials.

A revision switch is atomic for an individual request, not across a sequence of
client requests. Corrections must remain compatible within their SDK version;
semantic compatibility requires review and cannot be inferred from placeholders.
An installed retrieval skill remains untouched on a refresh failure, including
after SDK upgrade; an explicit reinstall uses the current SDK fallback. There is
no global latest pointer, automatic version eviction, or automatic rollback.
