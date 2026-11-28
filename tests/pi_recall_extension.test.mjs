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
  let idle = true;
  const ctx = {
    cwd: ".", isIdle: () => idle, ui: { notify() {} },
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
  return {
    handlers, calls, ctx, timers,
    setIdle: (value) => { idle = value; },
    switchSession: () => { session = "s2"; },
  };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

// Mirrors pi AgentSession.prompt + runAgentLoop ordering for idle and queued submissions.
function createSessionLoop(h) {
  const transcript = [];
  const steering = [];
  const followUp = [];
  const requests = [];
  let streaming = false;

  async function requestLlm() {
    const snapshot = structuredClone(transcript);
    const transformed = await h.handlers.context({ type: "context", messages: snapshot }, h.ctx);
    const messages = transformed?.messages ?? snapshot;
    requests.push(messages);
    return messages;
  }

  async function dequeueAndRequest(message) {
    await h.handlers.message_start({ type: "message_start", message }, h.ctx);
    transcript.push(message);
    return requestLlm();
  }

  return {
    requests,
    transcript,
    clearQueue() {
      steering.length = 0;
      followUp.length = 0;
    },
    async prompt(text, { source = "interactive", streamingBehavior } = {}) {
      await h.handlers.input({
        type: "input",
        text,
        source,
        streamingBehavior: streaming ? streamingBehavior : undefined,
      }, h.ctx);
      const userMessage = { role: "user", content: [{ type: "text", text }], timestamp: Date.now() };
      if (streaming) {
        if (!streamingBehavior) throw new Error("streamingBehavior required while streaming");
        (streamingBehavior === "followUp" ? followUp : steering).push(userMessage);
        return undefined;
      }
      const before = await h.handlers.before_agent_start({ type: "before_agent_start", prompt: text }, h.ctx);
      streaming = true;
      h.setIdle(false);
      const initial = [userMessage];
      if (before?.message) {
        initial.push({ role: "custom", ...before.message, timestamp: Date.now() });
      }
      for (const message of initial) {
        await h.handlers.message_start({ type: "message_start", message }, h.ctx);
        transcript.push(message);
      }
      return requestLlm();
    },
    async finishTurn({ toolCall = false, reply = "ok" } = {}) {
      if (toolCall) {
        transcript.push({ role: "assistant", content: [{ type: "toolCall", id: "t1", name: "read", arguments: {} }] });
        transcript.push({ role: "toolResult", toolCallId: "t1", toolName: "read", content: [{ type: "text", text: "done" }] });
      } else {
        transcript.push({ role: "assistant", content: [{ type: "text", text: reply }] });
      }
      if (steering.length > 0) return dequeueAndRequest(steering.shift());
      if (toolCall) return requestLlm();
      if (followUp.length > 0) return dequeueAndRequest(followUp.shift());
      streaming = false;
      h.setIdle(true);
      await h.handlers.agent_settled({ type: "agent_settled" }, h.ctx);
      return undefined;
    },
  };
}

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

test("queued steer and follow-up prompts retrieve synchronously and replace prior reference", async () => {
  const h = await setup();
  const loop = createSessionLoop(h);

  const firstPending = loop.prompt("save allergy");
  await flush();
  assert.equal(h.calls.at(-1).command, "prompt-hook");
  assert.equal(h.calls.at(-1).payload.prompt, "save allergy");
  h.calls.at(-1).complete({ context: "allergic to peanuts" });
  const firstReq = await firstPending;
  assert.equal(firstReq.filter((m) => m.customType === "memu-retrieval").length, 1);
  assert.match(firstReq.find((m) => m.customType === "memu-retrieval").content, /allergic to peanuts/);

  // Queue both a steer and a follow-up while the first turn is still streaming.
  await loop.prompt("what is for dinner?", { streamingBehavior: "steer" });
  await loop.prompt("any general cooking tips?", { streamingBehavior: "followUp" });
  assert.equal(h.calls.filter((c) => c.command === "prompt-hook").length, 1);

  // Finishing the first turn dequeues the steer prompt and awaits its recall in context.
  let steerReady = false;
  const steerPending = loop.finishTurn({ reply: "answer 1" }).then((v) => { steerReady = true; return v; });
  await flush();
  assert.equal(steerReady, false);
  assert.equal(h.calls.at(-1).command, "prompt-hook");
  assert.equal(h.calls.at(-1).payload.prompt, "what is for dinner?");
  h.calls.at(-1).complete({ context: "avoid peanuts at dinner" });
  const steerReq = await steerPending;
  const steerRefs = steerReq.filter((m) => m.customType === "memu-retrieval");
  assert.equal(steerRefs.length, 1);
  assert.match(steerRefs[0].content, /Retrieved for the current prompt\./);
  assert.match(steerRefs[0].content, /Source prompt \(JSON\): "what is for dinner\?"/);
  assert.match(steerRefs[0].content, /avoid peanuts at dinner/);
  assert.doesNotMatch(JSON.stringify(steerReq), /allergic to peanuts/);

  // Tool continuation on the steered prompt preserves its reference before tool call/result.
  const toolReq = await loop.finishTurn({ toolCall: true });
  assert.equal(h.calls.filter((c) => c.command === "prompt-hook").length, 2);
  const refIndex = toolReq.findIndex((m) => m.customType === "memu-retrieval");
  const lastUserIndex = toolReq.findLastIndex((m) => m.role === "user");
  const toolAssistantIndex = toolReq.findIndex((m) => m.role === "assistant" && m.content[0]?.type === "toolCall");
  assert.equal(refIndex, lastUserIndex + 1);
  assert.ok(refIndex < toolAssistantIndex);

  // Finishing the steered turn dequeues the follow-up; empty recall must clear prior reference.
  const followPending = loop.finishTurn({ reply: "answer 2" });
  await flush();
  assert.equal(h.calls.at(-1).command, "prompt-hook");
  assert.equal(h.calls.at(-1).payload.prompt, "any general cooking tips?");
  h.calls.at(-1).complete({ context: null });
  const followReq = await followPending;
  assert.equal(followReq.filter((m) => m.customType === "memu-retrieval").length, 0);
  assert.equal(h.calls.filter((c) => c.command === "memorize-hook").length, 0);

  await loop.finishTurn({ reply: "answer 3" });
  assert.equal(h.calls.filter((c) => c.command === "memorize-hook").length, 1);
  h.calls.at(-1).complete({});
});

test("queued follow-up and steer advance async recall boundaries without extra turns", async () => {
  const h = await setup(false);
  const loop = createSessionLoop(h);

  const firstReq = await loop.prompt("first question");
  assert.equal(firstReq.filter((m) => m.customType === "memu-retrieval").length, 0);
  const firstHook = h.calls.at(-1);
  assert.equal(firstHook.payload.prompt, "first question");

  // Submitting a follow-up while streaming must not kill in-flight recall for the active prompt.
  await loop.prompt("second question", { streamingBehavior: "followUp" });
  assert.equal(firstHook.killed, undefined);

  // Tool continuation on first question still runs while firstHook completes in background.
  firstHook.complete({ context: "memory from first" });
  await flush();
  assert.equal(h.calls.filter((c) => c.command === "memorize-hook").length, 0);
  const firstToolReq = await loop.finishTurn({ toolCall: true });
  assert.equal(firstToolReq.filter((m) => m.customType === "memu-retrieval").length, 0);

  // Dequeuing follow-up consumes completed first recall and starts second lookup without waiting.
  const secondReq = await loop.finishTurn({ reply: "answer 1" });
  const secondRefs = secondReq.filter((m) => m.customType === "memu-retrieval");
  assert.equal(secondRefs.length, 1);
  assert.match(secondRefs[0].content, /Retrieved for the previous prompt/);
  assert.match(secondRefs[0].content, /Source prompt \(JSON\): "first question"/);
  assert.match(secondRefs[0].content, /memory from first/);
  const secondHook = h.calls.at(-1);
  assert.equal(secondHook.command, "prompt-hook");
  assert.equal(secondHook.payload.prompt, "second question");

  // Steer queued and dequeued before secondHook finishes cancels secondHook and strips prior memory.
  await loop.prompt("third question", { streamingBehavior: "steer" });
  const thirdReq = await loop.finishTurn({ reply: "answer 2" });
  assert.equal(secondHook.killed, true);
  assert.equal(thirdReq.filter((m) => m.customType === "memu-retrieval").length, 0);
  const thirdHook = h.calls.at(-1);
  assert.equal(thirdHook.command, "prompt-hook");
  assert.equal(thirdHook.payload.prompt, "third question");

  // Settling waits for thirdHook before memorizing, and keeps thirdHook's result for the next prompt.
  await loop.finishTurn({ reply: "answer 3" });
  assert.equal(h.calls.filter((c) => c.command === "memorize-hook").length, 0);
  thirdHook.complete({ context: "memory from third" });
  await flush();
  assert.equal(h.calls.at(-1).command, "memorize-hook");
  h.calls.at(-1).complete({});

  const fourthReq = await loop.prompt("fourth question");
  const fourthRefs = fourthReq.filter((m) => m.customType === "memu-retrieval");
  assert.equal(fourthRefs.length, 1);
  assert.match(fourthRefs[0].content, /Source prompt \(JSON\): "third question"/);
  assert.match(fourthRefs[0].content, /memory from third/);
  h.handlers.session_shutdown();
});

test("extension-queued and cleared-queue inputs do not skip or leak into user prompts", async () => {
  const h = await setup();
  const loop = createSessionLoop(h);

  const firstPending = loop.prompt("user one");
  await flush();
  h.calls.at(-1).complete({ context: "first memory" });
  await firstPending;

  await loop.prompt("internal steer", { source: "extension", streamingBehavior: "steer" });

  // Extension steer skips prompt-hook and clears prior user memory for the internal turn.
  const hookCountBeforeExt = h.calls.filter((c) => c.command === "prompt-hook").length;
  const extReq = await loop.finishTurn({ reply: "answer 1" });
  assert.equal(h.calls.filter((c) => c.command === "prompt-hook").length, hookCountBeforeExt);
  assert.equal(extReq.filter((m) => m.customType === "memu-retrieval").length, 0);

  // Cleared extension/user queue entries must not skip a later user prompt with identical text.
  await loop.prompt("same text", { source: "extension", streamingBehavior: "steer" });
  await loop.prompt("abandoned follow-up", { source: "interactive", streamingBehavior: "followUp" });
  loop.clearQueue();
  await loop.finishTurn({ reply: "internal done" });
  assert.equal(h.calls.at(-1).command, "memorize-hook");
  h.calls.at(-1).complete({});

  const nextPending = loop.prompt("same text");
  await flush();
  assert.equal(h.calls.at(-1).command, "prompt-hook");
  assert.equal(h.calls.at(-1).payload.prompt, "same text");
  h.calls.at(-1).complete({ context: "second memory" });
  const nextReq = await nextPending;
  const nextRefs = nextReq.filter((m) => m.customType === "memu-retrieval");
  assert.equal(nextRefs.length, 1);
  assert.match(nextRefs[0].content, /second memory/);
  await loop.finishTurn({ reply: "answer 2" });
  h.calls.at(-1).complete({});
});

test("direct queued user messages retrieve and abort signal cancels pending recall", async () => {
  const h = await setup();
  const warnings = [];
  h.ctx.ui.notify = (msg) => { warnings.push(msg); };
  const abortController = new AbortController();
  h.ctx.signal = abortController.signal;

  // Direct RPC steer/follow_up dequeues at message_start without a preceding input event.
  await h.handlers.message_start({
    type: "message_start",
    message: { role: "user", content: [{ type: "text", text: "rpc steered prompt" }] },
  }, h.ctx);
  const pending = h.handlers.context({
    type: "context",
    messages: [{ role: "user", content: [{ type: "text", text: "rpc steered prompt" }] }],
  }, h.ctx);
  await flush();
  const child = h.calls.at(-1);
  assert.equal(child.command, "prompt-hook");
  assert.equal(child.payload.prompt, "rpc steered prompt");

  abortController.abort();
  const transformed = await pending;
  assert.equal(child.killed, true);
  assert.equal(warnings.length, 0);
  assert.equal(transformed.messages.filter((m) => m.customType === "memu-retrieval").length, 0);
});
