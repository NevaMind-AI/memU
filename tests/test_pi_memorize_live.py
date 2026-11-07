"""Opt-in acceptance against the installed memu-pi and real pi/model.

Run after uv tool install --force .:
MEMU_PI_LIVE_MODEL=provider/model uv run pytest tests/test_pi_memorize_live.py -s
Only embeddings use a local deterministic endpoint; storage is an isolated SQLite DB.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

LIVE_MODEL = os.environ.get("MEMU_PI_LIVE_MODEL")
pytestmark = pytest.mark.skipif(not LIVE_MODEL, reason="Opt-in live pi/model acceptance")


def test_installed_pi_memorize_and_retrieve(tmp_path):  # noqa: C901
    model_selection = LIVE_MODEL or ""
    provider, model = model_selection.split("/", 1)
    memu = shutil.which("memu-pi")
    launcher = shutil.which("pi")
    assert memu and launcher, "Install memu-cli and pi first"
    pi_argv = [launcher]
    if os.name == "nt":
        node = shutil.which("node")
        cli = Path(launcher).parent / "node_modules/@earendil-works/pi-coding-agent/dist/cli.js"
        assert node and cli.is_file()
        pi_argv = [node, str(cli)]
    calls = []

    class Embeddings(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            inputs = request["input"]
            if isinstance(inputs, str) or (inputs and isinstance(inputs[0], int)):
                inputs = [inputs]
            calls.append(len(inputs))
            body = json.dumps({
                "object": "list",
                "model": "acceptance-embedding",
                "data": [{"object": "embedding", "index": i, "embedding": [1.0, 0.0, 0.0]} for i in range(len(inputs))],
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Embeddings)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = tmp_path / "workspace"
    env = {
        **os.environ,
        "MEMU_MEMORY_MODE": "local",
        "MEMU_DB": str(tmp_path / "memory.sqlite3"),
        "MEMU_EMBED_PROVIDER": "openai",
        "MEMU_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
        "MEMU_API_KEY": "local-acceptance",
        "MEMU_EMBED_MODEL": "acceptance-embedding",
        "MEMU_TELEMETRY": "0",
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("MEMU_BRIDGING_RUN", None)
    subprocess.run(  # noqa: S603
        [memu, "install-prompt-hook", "--base-dir", str(base)],
        env={**env, "PI_CODING_AGENT_DIR": str(tmp_path / "agent")},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    extension = tmp_path / "agent/extensions/memu-retrieval.ts"
    project = tmp_path / "project"
    project.mkdir()
    process = subprocess.Popen(  # noqa: S603
        [
            *pi_argv,
            "--mode",
            "rpc",
            "--offline",
            "--session-dir",
            str(tmp_path / "source"),
            "--provider",
            provider,
            "--model",
            model,
            "--no-tools",
            "--no-skills",
            "--no-prompt-templates",
            "--no-context-files",
            "--no-extensions",
            "-e",
            str(extension),
            "--system-prompt",
            "Reply OK to user input. After a memu-retrieval custom message, reply CONTEXT_RECEIVED. Do not use tools.",
        ],
        cwd=project,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    stdin, stdout, stderr = process.stdin, process.stdout, process.stderr
    assert stdin is not None and stdout is not None and stderr is not None
    output: queue.Queue[dict] = queue.Queue()
    errors = []
    events = []

    def read_output():
        for line in stdout:
            try:
                output.put(json.loads(line))
            except ValueError:
                errors.append(line)

    threading.Thread(target=read_output, daemon=True).start()
    threading.Thread(target=lambda: errors.extend(stderr.readlines()), daemon=True).start()

    def send(payload):
        stdin.write(json.dumps(payload) + "\n")
        stdin.flush()

    log = None
    try:
        send({"type": "set_auto_retry", "enabled": False})
        send({
            "type": "prompt",
            "message": (
                "Please remember this durable convention for the isolated acceptance project Aurora: every release "
                "checklist must end with the phrase COPPER_PINE_73. This applies to every future Aurora release."
            ),
        })
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            try:
                event = output.get(timeout=0.5)
            except queue.Empty:
                event = {}
            if event.get("type") in ("agent_start", "agent_settled"):
                events.append(event["type"])
            assert event.get("type") != "extension_error", event
            if event.get("type") == "extension_ui_request":
                assert event.get("notifyType") not in ("warning", "error"), event
            logs = list((base / "log/hooks/memorize").glob("*.log"))
            if logs:
                log = logs[0]
                if "=== FINISHED pi exit=" in log.read_text(encoding="utf-8"):
                    break
        assert log is not None, errors
        contents = log.read_text(encoding="utf-8")
        assert "=== FINISHED pi exit=0 ===" in contents, contents[-12000:]
        assert "=== MEMORIZE status=succeeded ===" in contents
        assert len(list((base / "log/hooks/retrieve").glob("*.json"))) == 1
        assert len(list((base / "log/hooks/memorize").glob("*.log"))) == 1
        assert not list((base / "jobs").glob("*.txt")), "Commit must clear completed jobs"
        assert (base / "resources.md").exists(), "Resource verification must use the worker workspace"
        retrieved = subprocess.run(  # noqa: S603
            [memu, "retrieve", "What phrase must every Aurora release checklist end with?"],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=True,
        )
        assert "COPPER_PINE_73" in retrieved.stdout, retrieved.stdout
        assert calls, "Real local storage must call the embedding endpoint"
        print(
            json.dumps(
                {
                    "verified": True,
                    "events": events,
                    "worker_log": str(log),
                    "embedding_requests": len(calls),
                    "memorize_launches": 1,
                    "initial_retrieval_calls": 1,
                    "round_trip_fact": "COPPER_PINE_73",
                },
                indent=2,
            )
        )
    finally:
        if log is not None and "=== FINISHED pi exit=" not in log.read_text(encoding="utf-8"):
            pids = re.findall(r"=== (?:WORKER pi|AGENT) pid=(\d+)", log.read_text(encoding="utf-8"))
            for pid in reversed(pids):
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, check=False)  # noqa: S603, S607
                else:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(int(pid), signal.SIGKILL)
        try:
            send({"type": "abort"})
            stdin.close()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
            process.wait(timeout=3)
        server.shutdown()
        server.server_close()
