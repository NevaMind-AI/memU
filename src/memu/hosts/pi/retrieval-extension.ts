// memU managed retrieval extension. Installed by memu-pi install-prompt-hook.
import { spawn } from "node:child_process";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const executable = __MEMU_PYTHON__;
const baseDir = __MEMU_BASE_DIR__;

export default function (pi: ExtensionAPI) {
  let active = true;
  let generation = 0;
  let pendingMemorize = false;
  const retrievals = new Set<ReturnType<typeof spawn>>();
  pi.on("session_start", () => { active = true; });
  pi.on("session_shutdown", () => {
    active = false;
    pendingMemorize = false;
    generation += 1;
    for (const child of retrievals) child.kill();
    retrievals.clear();
  });

  function memorizeIfSettled(ctx: ExtensionContext) {
    if (!active || !pendingMemorize || retrievals.size || !ctx.isIdle()) return;
    pendingMemorize = false;
    const sessionFile = ctx.sessionManager.getSessionFile();
    if (!sessionFile) return;
    startHook("memorize-hook", {
      hook_event_name: "agent_settled",
      session_file: sessionFile,
      session_id: ctx.sessionManager.getSessionId(),
      provider: ctx.model?.provider,
      model: ctx.model?.id,
    }, ctx);
  }

  function startHook(command: string, payload: object, ctx: ExtensionContext) {
    const sessionId = ctx.sessionManager.getSessionId();
    const submittedGeneration = generation;
    const retrieving = command === "prompt-hook";
    const child = spawn(executable, ["-m", "memu.hosts.pi.cli", command, "--base-dir", baseDir], {
      cwd: ctx.cwd,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PI_SESSION_ID: sessionId, PYTHONIOENCODING: "utf-8" },
    });
    if (retrieving) retrievals.add(child);
    let output = "";
    let errors = "";
    child.stdout.setEncoding("utf8").on("data", (data) => { output += data; });
    child.stderr.setEncoding("utf8").on("data", (data) => { errors += data; });
    child.stdin.on("error", () => {}); // Spawn/exit handlers report failed children.
    child.on("error", (error) => {
      retrievals.delete(child);
      if (active && generation === submittedGeneration) ctx.ui.notify(`memU ${command}: ${error.message}`, "warning");
    });
    child.on("close", (code) => {
      retrievals.delete(child);
      if (!active || generation !== submittedGeneration || ctx.sessionManager.getSessionId() !== sessionId) return;
      try {
        if (code !== 0) throw new Error(errors.trim() || `exit ${code}`);
        const result = JSON.parse(output);
        if (!retrieving) return;
        if (typeof result.context === "string" && result.context) {
          pi.sendMessage({ customType: "memu-retrieval", content: result.context, display: false }, {
            triggerTurn: true,
            deliverAs: "steer",
          });
          return;
        }
      } catch (error) {
        ctx.ui.notify(`memU ${command}: ${error instanceof Error ? error.message : error}`, "warning");
      }
      if (retrieving) memorizeIfSettled(ctx);
    });
    child.stdin.end(JSON.stringify(payload));
  }

  pi.on("input", (event, ctx) => {
    if (event.source === "extension" || process.env.MEMU_BRIDGING_RUN?.trim() || !event.text.trim()) return;
    pendingMemorize = true;
    startHook("prompt-hook", { prompt: event.text, session_id: ctx.sessionManager.getSessionId(), source: event.source }, ctx);
    return { action: "continue" as const };
  });
  pi.on("agent_settled", (_event, ctx) => { memorizeIfSettled(ctx); });
}
