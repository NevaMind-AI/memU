import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { EventEmitter } from "node:events";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import { test } from "node:test";

const source = readFileSync(new URL("../src/memu/hosts/pi/retrieval-extension.ts", import.meta.url), "utf8")
  .replace('import { spawn } from "node:child_process";', "")
  .replace('import { randomUUID } from "node:crypto";', "")
  .replace("export default function", "function install")
  .replace("__MEMU_PYTHON__", '"python"').replace("__MEMU_BASE_DIR__", '"base"');
const javascript = stripTypeScriptTypes(source) + "\ninstall(pi);";

async function setup(sync = true) {
  const handlers = {};
  const calls = [];
  const timers = new Map();
  let session = "s1";
  const ctx = {
    cwd: ".", isIdle: () => true, ui: { notify() {} },
    sessionManager: { getSessionId: () => session, getSessionFile: () => "session.jsonl" },
  };
  const pi = {
    on: (event, handler) => { handlers[event] = handler; },
    sendMessage() { assert.fail("Recall must never schedule an extra answer"); },
  };
  function spawn(_executable, argv) {
    const child = new EventEmitter();
    child.command = argv[2];
    child.stdout = new EventEmitter(); child.stdout.setEncoding = () => child.stdout;
    child.stderr = { resume() {} };
    child.stdin = new EventEmitter(); child.stdin.end = (text) => { child.payload = JSON.parse(text); };
    child.kill = () => { child.killed = true; child.emit("close", null); };
    child.complete = (value) => { child.stdout.emit("data", JSON.stringify(value)); child.emit("close", 0); };
    calls.push(child);
    return child;
  }
  vm.runInNewContext(javascript, {
    pi, spawn, randomUUID, process: { env: {} },
    setTimeout: (fn) => { const id = {}; timers.set(id, fn); return id; },
    clearTimeout: (id) => timers.delete(id),
  });
  const startup = handlers.session_start({}, ctx);
  calls[0].complete({ recall_sync: sync });
  await startup;
  return { handlers, calls, ctx, timers, switchSession: () => { session = "s2"; } };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test("sync returns reference before the answer; memorize only after settled", async () => {
  const h = await setup();
  let finished = false;
  const result = h.handlers.before_agent_start({ prompt: "original task" }, h.ctx).then((v) => { finished = true; return v; });
  await flush();
  assert.equal(finished, false);
  h.calls.at(-1).complete({ context: "useful memory" });
  const reference = await result;
  assert.match(reference.message.content, /original task/);
  assert.match(reference.message.content, /useful memory/);
  assert.equal(reference.message.display, false);
  const messages = [
    { role: "custom", ...reference.message },
    { role: "custom", ...reference.message, details: { recallId: "older" } },
    { role: "user", content: "original task" },
  ];
  assert.equal(h.handlers.context({ messages }).messages.length, 2);
  assert.equal(h.calls.filter((c) => c.command === "memorize-hook").length, 0);
  h.handlers.agent_settled({}, h.ctx);
  assert.equal(h.calls.at(-1).command, "memorize-hook");
  h.calls.at(-1).complete({});
});

test("async completes after the answer without steering; injects once next prompt", async () => {
  const h = await setup(false);
  assert.equal(await h.handlers.before_agent_start({ prompt: "first" }, h.ctx), undefined);
  const first = h.calls.at(-1);
  h.handlers.agent_settled({}, h.ctx);
  assert.equal(h.calls.at(-1), first);
  first.complete({ context: "previous memory" });
  await flush();
  assert.equal(h.calls.at(-1).command, "memorize-hook");
  h.calls.at(-1).complete({});
  const next = await h.handlers.before_agent_start({ prompt: "second" }, h.ctx);
  assert.match(next.message.content, /previous prompt/);
  assert.match(next.message.content, /Source prompt \(JSON\): "first"/);
  h.calls.at(-1).complete({ context: null });
  await flush();
  assert.equal(await h.handlers.before_agent_start({ prompt: "third" }, h.ctx), undefined);
  h.handlers.session_shutdown();
});

test("deadline returns no context and ignores a late result", async () => {
  const h = await setup();
  const pending = h.handlers.before_agent_start({ prompt: "task" }, h.ctx);
  const child = h.calls.at(-1);
  [...h.timers.values()][0]();
  assert.equal(await pending, undefined);
  assert.equal(child.killed, true);
  child.complete({ context: "late" });
  h.handlers.agent_settled({}, h.ctx);
  h.calls.at(-1).complete({});
});

test("session reset discards pending results; old reference messages are filtered", async () => {
  const h = await setup();
  const pending = h.handlers.before_agent_start({ prompt: "task" }, h.ctx);
  h.switchSession();
  h.handlers.session_shutdown();
  assert.equal(await pending, undefined);
  const messages = [{ role: "user", content: "task" }, { role: "custom", customType: "memu-retrieval", content: "old" }];
  assert.equal(h.handlers.context({ messages }).messages.length, 1);
});

test("pending previous recall is cancelled rather than injected late", async () => {
  const h = await setup(false);
  await h.handlers.before_agent_start({ prompt: "first" }, h.ctx);
  const first = h.calls.at(-1);
  assert.equal(await h.handlers.before_agent_start({ prompt: "second" }, h.ctx), undefined);
  assert.equal(first.killed, true);
  first.complete({ context: "stale" });
  h.calls.at(-1).complete({ context: null });
  await flush();
  assert.equal(await h.handlers.before_agent_start({ prompt: "third" }, h.ctx), undefined);
  h.handlers.session_shutdown();
});

test("extension input skips recall and empty results do not inject", async () => {
  const h = await setup();
  h.handlers.input({ source: "extension" });
  assert.equal(await h.handlers.before_agent_start({ prompt: "internal" }, h.ctx), undefined);
  assert.equal(h.calls.length, 1);
  const pending = h.handlers.before_agent_start({ prompt: "user" }, h.ctx);
  h.calls.at(-1).complete({ context: null });
  assert.equal(await pending, undefined);
});


test("hook failures and malformed output leave the original task runnable", async () => {
  for (const failure of ["error", "nonzero", "invalid"]) {
    const h = await setup();
    const pending = h.handlers.before_agent_start({ prompt: "original task" }, h.ctx);
    const child = h.calls.at(-1);
    if (failure === "error") child.emit("error", new Error("spawn failed"));
    if (failure === "nonzero") child.emit("close", 1);
    if (failure === "invalid") { child.stdout.emit("data", "bad JSON"); child.emit("close", 0); }
    assert.equal(await pending, undefined);
    h.handlers.agent_settled({}, h.ctx);
    assert.equal(h.calls.at(-1).command, "memorize-hook");
    h.calls.at(-1).complete({});
  }
});
