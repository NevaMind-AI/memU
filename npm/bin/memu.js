#!/usr/bin/env node
// memu-cli: thin launcher for the PyPI package `memu-cli` (the CLI release
// channel of the memU engine; same module as memu-py, versioned independently).
//
// The memU engine is Python (>= 3.13). This shim finds a runner and delegates,
// in order of preference:
//   1. $MEMU_PYTHON -m memu            (explicit interpreter override)
//   2. uvx --from memu-cli memu        (no install needed, cached by uv)
//   3. pipx run --spec memu-cli memu   (no install needed, cached by pipx)
//   4. python3 -m memu                 (requires `pip install memu-cli`)
"use strict";

const { spawnSync } = require("node:child_process");

const args = process.argv.slice(2);

function has(cmd) {
  const probe = spawnSync(cmd, ["--version"], { stdio: "ignore", shell: false });
  return probe.error === undefined && probe.status === 0;
}

function run(cmd, prefix) {
  const child = spawnSync(cmd, [...prefix, ...args], { stdio: "inherit", shell: false });
  if (child.error) {
    console.error(`memu-cli: failed to launch ${cmd}: ${child.error.message}`);
    process.exit(1);
  }
  process.exit(child.status === null ? 1 : child.status);
}

if (process.env.MEMU_PYTHON) {
  run(process.env.MEMU_PYTHON, ["-m", "memu"]);
}
if (has("uvx")) {
  run("uvx", ["--from", "memu-cli", "memu"]);
}
if (has("pipx")) {
  run("pipx", ["run", "--spec", "memu-cli", "memu"]);
}
if (has("python3")) {
  const probe = spawnSync("python3", ["-c", "import memu"], { stdio: "ignore" });
  if (probe.status === 0) {
    run("python3", ["-m", "memu"]);
  }
}

console.error(
  [
    "memu-cli: no Python runner found. The memU engine is the PyPI package `memu-cli` (Python >= 3.13).",
    "Install one of:",
    "  - uv    (https://docs.astral.sh/uv/)  -> memu-cli will use `uvx` automatically",
    "  - pipx  (https://pipx.pypa.io/)       -> memu-cli will use `pipx run` automatically",
    "  - pip   -> `pip install memu-cli`, then re-run",
    "Or point MEMU_PYTHON at an interpreter that has memU installed.",
  ].join("\n")
);
process.exit(1);
