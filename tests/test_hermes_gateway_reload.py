"""Installation must distinguish disk verification from live gateway activation."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from memu.hosts.hermes import hook_install


@pytest.mark.parametrize("outcome", ["confirmed", "unreachable", "refused", "missing-hook", "invalid-json", "error"])
def test_reload_validates_native_activation(monkeypatch, outcome):
    monkeypatch.setattr(hook_install.shutil, "which", lambda _: sys.executable)
    calls = []

    def execute(python, *argv):
        calls.append((python, argv))
        assert python == sys.executable
        assert argv[0] == "-c" and "reload_running_gateway" in argv[1]
        if outcome == "error":
            raise RuntimeError("host startup failed")  # noqa: TRY003
        if outcome == "invalid-json":
            return "bad JSON"
        if outcome == "unreachable":
            return "null"
        return json.dumps({
            "reloaded": outcome != "refused",
            "activations": [
                {
                    "key": "memu-memory",
                    "activated_now": {
                        "hooks": ["pre_llm_call", "on_session_end"]
                        + (["on_session_finalize"] if outcome != "missing-hook" else [])
                    },
                }
            ],
        })

    monkeypatch.setattr(hook_install, "_run", execute)
    if outcome in {"confirmed", "unreachable"}:
        assert hook_install.reload_gateway() == {
            "gateway_reload": "confirmed" if outcome == "confirmed" else "unconfirmed",
            "restart_required": outcome != "confirmed",
        }
    else:
        with pytest.raises((RuntimeError, ValueError)):
            hook_install.reload_gateway()
    assert len(calls) == 1


def test_reload_without_host_python_requires_restart(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_install.shutil, "which", lambda _: str(tmp_path / "hermes"))
    monkeypatch.setattr(hook_install, "_run", lambda *a: pytest.fail("must not guess another interpreter"))
    assert hook_install.reload_gateway() == {"gateway_reload": "unconfirmed", "restart_required": True}


def test_worker_delegates_profile_resolution_to_hermes(monkeypatch, tmp_path, capsys):
    from memu.hosts.hermes import reload_worker

    paths = list(sys.path)
    monkeypatch.setattr(sys, "path", paths)
    monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(__file__=str(tmp_path / "hermes_cli/__init__.py")))
    monkeypatch.setitem(sys.modules, "hermes_bootstrap", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules, "hermes_cli.plugins_activation", SimpleNamespace(reload_running_gateway=lambda: {"reloaded": True})
    )
    reload_worker.main()
    assert json.loads(capsys.readouterr().out) == {"reloaded": True}
    assert sys.path[0] == str(tmp_path)
