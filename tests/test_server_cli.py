from __future__ import annotations

from memu.server.cli import main


def test_server_cli_stub_message(capsys) -> None:
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "compatibility stub" in out
    assert "memU-server" in out


def test_server_cli_version(capsys) -> None:
    exit_code = main(["--version"])
    out = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert out.startswith("memu ")

