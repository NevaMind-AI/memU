// SDK assets are release artifacts. Never fall through to the marketing site.
const assetPath = /^(?:instructions\/[a-z-]+\.txt|docs\/[a-z-]+\/(?:INSTALL|BRIDGING_TASK|UNINSTALL)\.md)$/;
const headers = {
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};
const error = (status, message) => new Response(message, { status, headers });

export default {
  async fetch(request, env) {
    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method not allowed", { status: 405, headers: { ...headers, Allow: "GET, HEAD" } });
    }
    const path = new URL(request.url).pathname;
    const match = /^\/sdk\/([0-9][a-zA-Z0-9.!+_-]*)\/(.+)$/.exec(path);
    if (!match) return error(404, "Not found");
    const [, version, name] = match;
    if (name !== "manifest.json" && !assetPath.test(name)) return error(404, "Not found");
    try {
      const pointer = await env.SDK_ASSETS.get(`sdk/${version}/current.json`);
      if (!pointer) return error(404, "SDK version not published");
      const manifest = await pointer.json();
      if (manifest.schema !== 1 || manifest.sdk_version !== version ||
          !/^[a-f0-9]{64}$/.test(manifest.revision) || !manifest.files) {
        return error(502, "Invalid publication manifest");
      }
      if (name === "manifest.json") {
        return new Response(request.method === "HEAD" ? null : JSON.stringify(manifest), {
          headers: { ...headers, "Content-Type": "application/json", "X-Memu-Revision": manifest.revision },
        });
      }
      const info = Object.hasOwn(manifest.files, name) && manifest.files[name];
      if (!info) return error(404, "Asset not published");
      const object = await env.SDK_ASSETS.get(`sdk/${version}/revisions/${manifest.revision}/${name}`);
      if (!object) return error(502, "Incomplete publication");
      const body = await object.arrayBuffer();
      if (body.byteLength > 65536 || body.byteLength !== info.size) return error(502, "Invalid asset size");
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", body)))
        .map(byte => byte.toString(16).padStart(2, "0")).join("");
      if (hash !== info.sha256) return error(502, "Asset checksum mismatch");
      return new Response(request.method === "HEAD" ? null : body, {
        headers: {
          ...headers,
          "Content-Type": name.endsWith(".md") ? "text/markdown; charset=utf-8" : "text/plain; charset=utf-8",
          ETag: `"${hash}"`,
          "X-Memu-Revision": manifest.revision,
        },
      });
    } catch {
      return error(503, "SDK assets temporarily unavailable");
    }
  },
};
