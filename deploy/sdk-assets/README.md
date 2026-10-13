# Versioned SDK assets

The memU release owns its instruction templates and per-host guides. The website
repository is not involved. Public URLs use the wheel METADATA version explicitly
normalized with `packaging.version.Version` (`0.11.0-beta.3` becomes `0.11.0b3`):

```text
https://memu.pro/sdk/0.11.0b3/instructions/memory-job.txt
https://memu.pro/sdk/0.11.0b3/docs/claude-code/INSTALL.md
https://memu.pro/sdk/0.11.0b3/manifest.json
```

## Export rules

`scripts/sdk_assets.py export` reads the **installed distribution**, not arbitrary
files from the working tree. Release CI runs it in an isolated environment with
exactly the wheel being published. It exports:

- `memory-job.txt` and `skill-job.txt` from `hosts/bridging/instructions.py`.
- `resource-job.txt` from `hosts/bridging/resources.py`.
- The complete retrieval skill from `hosts/instruction.py`, retaining `{binary}`.
- `INSTALL.md`, `BRIDGING_TASK.md`, and `UNINSTALL.md` from each packaged host.
  The URL host id comes from that adapter's `HOST` declaration: `claude_code`
  becomes `claude-code`, and `generic` becomes `agent`. Hosts are discovered from
  the package rather than maintained in a separate list.

Currently this produces 31 assets. Export rejects invalid placeholders, empty or
oversize assets, and missing guides. The manifest records the SDK version, source
commit, file sizes, SHA-256 hashes, and a deterministic revision id. Generated
assets live under ignored `dist/`, not in Git. The website's `/SKILL.md` remains
its separately maintained installation entry point.

## One-time Cloudflare setup

1. Create a **private** R2 bucket named `memu-sdk-assets`, or update the name in
   `wrangler.toml`. No public R2 domain or upload HTTP service is required.
2. Check `wrangler.toml`: its route is `memu.pro/sdk/*`. The DNS hostname must be
   proxied through Cloudflare in the appropriate zone. If the canonical hostname
   is `memu.so`, change the route/zone and the SDK defaults together, or configure
   routes on both zones. Exclude `/sdk/*` from any existing whole-site redirect
   and cache rules: a redirect rule may run before a Worker route.
3. Deploy the read-only Worker with your existing Cloudflare tooling:

   ```bash
   npx wrangler@4 deploy --config deploy/sdk-assets/wrangler.toml
   ```

   Worker changes are deployed separately; publishing assets does not redeploy
   the Worker. Its only runtime binding is `SDK_ASSETS` to the bucket. No server,
   database, upload endpoint, or Worker runtime secret is needed.
4. Create a bucket-scoped **Object Read & Write** R2 API credential for CI. In
   GitHub, create an environment named `sdk-assets`, with these secrets:

   | Secret | Value |
   | --- | --- |
   | `R2_ACCESS_KEY_ID` | R2 S3 access key id |
   | `R2_SECRET_ACCESS_KEY` | R2 S3 secret access key |

5. Set these **repository Actions variables** (the bucket variable also enables
   the SDK asset job in the normal PyPI release workflow):

   | Variable | Value |
   | --- | --- |
   | `SDK_ASSETS_BUCKET` | `memu-sdk-assets` |
   | `SDK_ASSETS_R2_ENDPOINT` | The bucket's S3 endpoint, usually `https://<account-id>.r2.cloudflarestorage.com` |
   | `SDK_ASSETS_PUBLIC_BASE_URL` | Optional; defaults to `https://memu.pro/sdk` |

   Environment reviewers may be configured according to the team's publishing
   policy. The workflow checks for the AWS CLI available on GitHub's Ubuntu
   runner; local uploads also require AWS CLI. Worker deployment uses separate
   Cloudflare deployment permissions, not the R2 object credential.

## Normal release

`publish-memu-cli.yml` exports the assets from the same wheel it sends to PyPI.
After successful PyPI publication, it invokes `sdk-assets-upload.yml` if
`SDK_ASSETS_BUCKET` is configured. Until configured, it exports an artifact but
performs no remote upload. Missing assets cause SDK fallback, so a delayed or
failed upload does not block users of the newly released wheel. Normal PyPI
publication rejects an already-published version instead of silently skipping
it: otherwise a newly built, different wheel could supply instructions for the
older PyPI package. To retry only a failed asset upload, use the asset-only
workflow from the same source commit and version; identical publication is a no-op.

The uploader validates all local hashes **before** writing anything. It uploads a
complete snapshot, followed by the active manifest:

```text
sdk/<version>/revisions/<revision>/<asset>
sdk/<version>/revisions/<revision>/manifest.json
sdk/<version>/current.json
```

The Worker resolves each request through `current.json`. Failed uploads leave the
previous pointer intact; a first failed upload leaves that version unpublished.
Publication does not delete previous snapshots or other SDK versions. CI
serializes both normal and manual publications; do not run external writers
concurrently with it. An identical retry is a no-op. A different publication of
an existing version requires explicit `--overwrite`.

After upload, CI requests the public manifest and all assets and verifies their
hashes. A failure makes the workflow fail; enable GitHub Actions failure
notifications for the owning team. It does not automatically undo a publication.

## Compatible wording corrections

Use **publish SDK assets only** (`publish-sdk-assets.yml`), selecting a reviewed
maintenance branch based on the target SDK release, setting its version, and
checking `overwrite`. This builds a temporary wheel to export the corrected
instructions; it does **not** publish that wheel to PyPI.

Only modify the instruction strings or raw host guides for this operation. Keep
all placeholders and referenced commands compatible with the target installed
SDK. Do not select current `main` and relabel new SDK instructions as an older
version: neither placeholder validation nor hashes prove semantic compatibility.
Keep corrections in Git so their commit is recorded in the manifest.

The Worker bypasses CDN caching by reading R2 directly and returns `no-store` for
successes and failures. There is no long-lived `immutable` caching on the public
version URL. SDK jobs attempt refresh during `prepare` at most once per URL
per 24 hours, including failed attempts; wording updates may therefore take up
to the next eligible prepare run to arrive. Docs fetch on each `docs` command,
and the retrieval skill on installation or its scheduled refresh, not every turn.
Job/doc caches are scoped to the SDK version; old unversioned caches are ignored.
Older SDKs that still request unversioned `/sdk/instructions/` or `/sdk/docs/`
receive 404 and continue using their existing fallback. Do not add a `latest`
alias for these clients. SDKs must be upgraded to use the versioned URLs.

Existing installed retrieval skills still follow the established refresh policy:
on fetch failure, leave the installed copy alone. Re-run `install-instruction`
after an SDK upgrade if that copy must be reset to the new embedded default.

Each HTTP request uses one complete snapshot. Several separate SDK fetches can
straddle a pointer switch; corrections must therefore remain compatible with the
preceding revision of the same SDK version. There is no session-wide snapshot
pinning. A missing version/file returns 404; invalid storage content returns a
non-200 response. Nothing redirects to `latest`, another SDK version, or HTML.

## Local export, upload, verification, and rollback

From the repository root, with your release wheel already built:

```bash
# Use an empty output path; export refuses to overwrite a local directory.
uv run --no-project --isolated --with /absolute/path/memu_cli-0.11.0b3-py3-none-any.whl \
  python scripts/sdk_assets.py export --output dist/sdk-assets --source-commit <commit-sha>

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY come from your credential manager.
python3 scripts/sdk_assets.py upload --directory dist/sdk-assets \
  --bucket memu-sdk-assets --endpoint https://<account-id>.r2.cloudflarestorage.com

python3 scripts/sdk_assets.py verify --directory dist/sdk-assets
```

For a correction, add `--overwrite` to the upload command. Upload/verify only use
Python's standard library plus the AWS CLI; exporting needs the installed wheel.

To roll back, download a previous `sdk/<version>/revisions/<revision>/` prefix
with `aws s3 sync` into a fresh local directory, then use the same upload command
with `--overwrite` and run verification. The snapshot contains its original
manifest, so rollback restores the exact earlier file set. Do not expire old
versions or snapshots automatically: older SDK installations may still use them.

## Checks

```bash
uv run python -m pytest tests/test_sdk_assets.py tests/test_host_templates.py
node --test deploy/sdk-assets/worker.test.mjs
```

Python tests cover raw exports, host mapping, checksum validation, partial-upload
failure, overwrite policy, public verification, and version cache isolation.
Worker tests cover read responses, missing versions, invalid publications,
revision switching, and storage failures without needing Cloudflare credentials.
These mocks do not replace the public verification after real deployment.

References: [R2 with AWS CLI](https://developers.cloudflare.com/r2/examples/aws/aws-cli/),
[Worker routes](https://developers.cloudflare.com/workers/configuration/routing/routes/),
[R2 consistency and caching](https://developers.cloudflare.com/r2/reference/consistency/).
