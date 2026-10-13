import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import worker from "./worker.mjs";

const version = "0.11.0b3";
const revision = "a".repeat(64);
const name = "instructions/memory-job.txt";
const body = "job {input_path} {track_dir}";
const hash = createHash("sha256").update(body).digest("hex");
const manifest = {
  schema: 1, sdk_version: version, revision,
  files: { [name]: { sha256: hash, size: Buffer.byteLength(body) } },
};
const key = `sdk/${version}/revisions/${revision}/${name}`;
function bucket(objects = {}) {
  return { SDK_ASSETS: { async get(key) {
    if (!(key in objects)) return null;
    return {
      async json() { return JSON.parse(objects[key]); },
      async arrayBuffer() { return new TextEncoder().encode(objects[key]).buffer; },
    };
  } } };
}
function published(extra = {}) {
  return bucket({ [`sdk/${version}/current.json`]: JSON.stringify(manifest), [key]: body, ...extra });
}
const request = (path = `${version}/${name}`, method = "GET") => new Request(`https://memu.pro/sdk/${path}`, { method });

test("serves checked UTF-8 content and HEAD without persistent caching", async () => {
  const response = await worker.fetch(request(), published());
  assert.equal(response.status, 200);
  assert.equal(await response.text(), body);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.match(response.headers.get("Content-Type"), /text\/plain/);
  assert.equal((await worker.fetch(request(undefined, "HEAD"), published())).body, null);
});

test("unknown versions and unpublished paths are 404, never HTML fallbacks", async () => {
  for (const path of [`0.12.0/${name}`, "instructions/memory-job.txt", `${version}/current.json`, `${version}/docs/codex/UNKNOWN.md`]) {
    assert.equal((await worker.fetch(request(path), published())).status, 404);
  }
  assert.equal((await worker.fetch(request(), bucket())).status, 404);
});

test("failed publication and corrupted bodies are rejected", async () => {
  assert.equal((await worker.fetch(request(), bucket({ [`sdk/${version}/current.json`]: JSON.stringify(manifest) }))).status, 502);
  assert.equal((await worker.fetch(request(), published({ [key]: "bad" }))).status, 502);
  assert.equal((await worker.fetch(request(), published({ [key]: body.replace("job", "bad") }))).status, 502);
  assert.equal((await worker.fetch(request(), published({ [`sdk/${version}/current.json`]: "invalid" }))).status, 503);
});

test("same URL sees the next revision, and manifest exposes the active snapshot", async () => {
  const updated = { ...manifest, revision: "b".repeat(64) };
  const env = published({
    [`sdk/${version}/current.json`]: JSON.stringify(updated),
    [`sdk/${version}/revisions/${updated.revision}/${name}`]: body,
  });
  const response = await worker.fetch(request(), env);
  assert.equal(response.headers.get("X-Memu-Revision"), updated.revision);
  assert.deepEqual(await (await worker.fetch(request(`${version}/manifest.json`), env)).json(), updated);
});

test("writes are refused and storage failures return a non-success response", async () => {
  assert.equal((await worker.fetch(request(undefined, "POST"), published())).status, 405);
  const env = { SDK_ASSETS: { async get() { throw new Error("offline"); } } };
  assert.equal((await worker.fetch(request(), env)).status, 503);
});
