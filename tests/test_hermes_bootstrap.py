"""Hermes's console-script boundary isolates its embedded Python on Windows."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from memu.hosts import host_cli
from memu.hosts.hermes.cli import SPEC
from memu_hermes_bootstrap import hermes as bootstrap


def test_non_windows_delegates_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.hosts.hermes import cli

    monkeypatch.setattr(bootstrap.os, "name", "posix")
    monkeypatch.setattr(cli, "main", lambda: 23)

    def unexpected_call(*args: Any, **kwargs: Any) -> int:
        raise AssertionError

    monkeypatch.setattr(bootstrap.subprocess, "call", unexpected_call)

    assert bootstrap.main() == 23


def test_windows_restarts_with_clean_import_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_call(command: list[str], *, env: dict[str, str]) -> int:
        captured["command"] = command
        captured["env"] = env
        return 17

    monkeypatch.setattr(bootstrap.os, "name", "nt")
    monkeypatch.setattr(bootstrap.sys, "executable", r"C:\Python313\python.exe")
    monkeypatch.setattr(bootstrap.sys, "argv", ["memu-hermes", "retrieve", "tea and cake"])
    monkeypatch.setattr(bootstrap.subprocess, "call", fake_call)
    monkeypatch.setenv("PYTHONPATH", r"C:\hermes;C:\hermes\venv\Lib\site-packages")
    monkeypatch.setenv("PYTHONHOME", r"C:\hermes\venv")
    monkeypatch.setenv("VIRTUAL_ENV", r"C:\hermes\venv")
    monkeypatch.setenv("MEMU_DB", r"C:\memory\memu.sqlite3")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example")

    assert bootstrap.main() == 17
    assert captured["command"] == [
        r"C:\Python313\python.exe",
        "-E",
        "-P",
        "-m",
        "memu.hosts.hermes.cli",
        "retrieve",
        "tea and cake",
    ]
    child_env = captured["env"]
    assert "PYTHONPATH" not in child_env
    assert "PYTHONHOME" not in child_env
    assert "VIRTUAL_ENV" not in child_env
    assert child_env[bootstrap.ISOLATED_ENV_MARKER] == "PYTHONPATH,PYTHONHOME,VIRTUAL_ENV"
    assert child_env["MEMU_DB"] == r"C:\memory\memu.sqlite3"
    assert child_env["HTTPS_PROXY"] == "http://proxy.example"


def test_windows_ctrl_c_returns_shell_interrupt_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.os, "name", "nt")

    def interrupted(*args: Any, **kwargs: Any) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(bootstrap.subprocess, "call", interrupted)

    assert bootstrap.main() == 130


def test_doctor_debug_reports_isolated_variable_names(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def successful_retrieve(query: str) -> dict[str, list[Any]]:
        return {"segments": [], "files": [], "resources": []}

    monkeypatch.setattr(host_cli.retrieval, "retrieve", successful_retrieve)
    monkeypatch.setenv("MEMU_MEMORY_MODE", "local")
    monkeypatch.setenv("MEMU_DB", ":memory:")
    monkeypatch.setenv("MEMU_DEBUG", "1")
    monkeypatch.setenv(bootstrap.ISOLATED_ENV_MARKER, "PYTHONPATH,VIRTUAL_ENV")

    assert host_cli.run(SPEC, ["doctor"]) == 0
    assert "isolated Hermes host Python environment (PYTHONPATH,VIRTUAL_ENV)" in capsys.readouterr().err


class _CloudHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body = b'{"segments": [], "files": [], "resources": []}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        pass


def _console_script() -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    return Path(sys.executable).with_name(f"memu-hermes{suffix}")


def test_installed_console_script_survives_hermes_pythonpath(tmp_path: Path) -> None:
    script = _console_script()
    assert script.is_file(), f"installed console script not found: {script}"

    env = os.environ.copy()
    env["MEMU_DOCS_BASE_URL"] = ""
    env["MEMU_TEMPLATE_BASE_URL"] = ""
    env["MEMU_MEMORY_MODE"] = "cloud"
    env["MEMU_CLOUD_API_KEY"] = "test-key"
    env["MEMU_DEBUG"] = "1"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = "127.0.0.1,localhost"

    if sys.platform == "win32":
        hermes_site = tmp_path / "hermes-venv" / "Lib" / "site-packages"
        hermes_site.mkdir(parents=True)
        (hermes_site / "pydantic.py").write_text(
            'raise RuntimeError("poisoned Hermes pydantic was imported")\n', encoding="utf-8"
        )
        env["PYTHONPATH"] = str(hermes_site)
        env["VIRTUAL_ENV"] = str(tmp_path / "hermes-venv")

    docs = subprocess.run(  # noqa: S603
        [str(script), "docs", "install"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert docs.returncode == 0, docs.stderr
    assert "Install memU for Hermes Agent" in docs.stdout

    server = ThreadingHTTPServer(("127.0.0.1", 0), _CloudHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env["MEMU_CLOUD_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/api/v4/memory/"
        doctor = subprocess.run(  # noqa: S603
            [str(script), "doctor"],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert doctor.returncode == 0, doctor.stderr
    assert "retrieval ok" in doctor.stdout
    if sys.platform == "win32":
        assert "isolated Hermes host Python environment (PYTHONPATH,VIRTUAL_ENV)" in doctor.stderr
