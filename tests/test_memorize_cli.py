from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from memu import cli
from memu.app.memorize.lifecycle import PreparedMemorizeRun
from memu.app.memorize.materialize import MaterializedConversation


def _payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "items": [{"type": "message", "role": "user", "content": "Remember this"}],
    }


def _prepared(workspace: Any, jobs: tuple[str, ...] = ("1.txt", "2.txt", "3.txt")) -> PreparedMemorizeRun:
    return PreparedMemorizeRun(
        transcripts=[MaterializedConversation(
            memory_path=workspace.input / "1.jsonl",
            skill_path=workspace.input / "1_full.jsonl",
        )],
        jobs=[workspace.jobs / name for name in jobs],
    )


def test_parser_covers_memorize_actions() -> None:
    parser = cli.build_parser()
    for argv in (
        ["memorize", "prepare", "input.json"],
        ["memorize", "commit"],
        ["memorize", "verify-resources"],
    ):
        assert callable(parser.parse_args(argv).handler)

    with pytest.raises(SystemExit):
        parser.parse_args(["memorize", "commit", "--workspace", "custom"])


def test_prepare_uses_fixed_workspace_and_prints_agent_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = tmp_path / "input.json"
    payload.write_text(json.dumps(_payload()), encoding="utf-8")
    workspace = tmp_path / "developer"
    backend = object()
    received: dict[str, Any] = {}

    async def fake_prepare(memorize_input: Any, prepared_workspace: Any, selected_backend: Any, **kwargs: Any) -> Any:
        received.update({
            "input": memorize_input,
            "workspace": prepared_workspace,
            "backend": selected_backend,
            **kwargs,
        })
        return _prepared(prepared_workspace)

    monkeypatch.setattr(cli, "MEMORIZE_WORKSPACE", str(workspace))
    monkeypatch.setattr(cli, "_build_backend", lambda _args: backend)
    monkeypatch.setattr(cli, "prepare_memorize", fake_prepare)

    assert cli.main(["memorize", "prepare", str(payload)]) == 0

    assert received["input"][0].items[0].content == "Remember this"
    assert received["workspace"].base == workspace
    assert received["backend"] is backend
    assert received["verify_command"] == "memu memorize verify-resources"
    output = capsys.readouterr().out
    assert "prepared developer session" in output
    assert "3 job(s)" in output
    assert "run one external agent session with this prompt:" in output
    assert "1. " + str(workspace / "jobs" / "1.txt") in output
    assert "2. " + str(workspace / "jobs" / "2.txt") in output
    assert "3. " + str(workspace / "jobs" / "3.txt") in output
    assert "Do not parallelize, skip, or reorder jobs" in output
    assert "Do not run `memu memorize commit`" in output
    assert "after the agent reports success, run:" in output
    assert "memu memorize commit" in output


def test_prepare_reads_stdin_and_prints_machine_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "workspace"

    async def fake_prepare(_memorize_input: Any, prepared_workspace: Any, _backend: Any, **_kwargs: Any) -> Any:
        return _prepared(prepared_workspace, ("1.txt",))

    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(_payload())))
    monkeypatch.setattr(cli, "MEMORIZE_WORKSPACE", str(workspace))
    monkeypatch.setattr(cli, "_build_backend", lambda _args: object())
    monkeypatch.setattr(cli, "prepare_memorize", fake_prepare)

    assert cli.main(["memorize", "prepare", "-", "--json"]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output == {
        "workspace": str(workspace),
        "transcript": {
            "memory_path": str(workspace / "input" / "1.jsonl"),
            "skill_path": str(workspace / "input" / "1_full.jsonl"),
        },
        "jobs": [str(workspace / "jobs" / "1.txt")],
        "executor_prompt": (
            "Process this prepared memU self-evolve run in one agent session.\n"
            "Read and carry out every job file below in the listed order:\n"
            f"1. {workspace / 'jobs' / '1.txt'}\n"
            "Run one job at a time. Do not parallelize, skip, or reorder jobs. "
            "If any job fails, stop and report failure. Do not run `memu memorize commit`. "
            "Report success only after every job has completed."
        ),
        "next_command": "memu memorize commit",
    }


def test_prepare_multiple_files_passes_all_sessions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = [tmp_path / f"{index}.json" for index in range(2)]
    for index, payload in enumerate(payloads):
        payload.write_text(json.dumps(_payload() | {"items": [{"type": "message", "role": "user", "content": str(index)}]}), encoding="utf-8")
    received: dict[str, Any] = {}

    async def fake_prepare(inputs: Any, workspace: Any, _backend: Any, **_kwargs: Any) -> Any:
        received["inputs"] = inputs
        return _prepared(workspace)

    monkeypatch.setattr(cli, "_build_backend", lambda _args: object())
    monkeypatch.setattr(cli, "prepare_memorize", fake_prepare)

    assert cli.main(["memorize", "prepare", *(str(path) for path in payloads)]) == 0
    assert [item.items[0].content for item in received["inputs"]] == ["0", "1"]


def test_executor_prompt_preserves_returned_job_order(tmp_path: Path) -> None:
    workspace = cli.MemorizeWorkspace(tmp_path / "workspace")
    prepared = _prepared(workspace, ("8.txt", "3.txt", "11.txt"))

    prompt = cli._memorize_executor_prompt(prepared)

    assert prompt.index(f"1. {workspace.jobs / '8.txt'}") < prompt.index(f"2. {workspace.jobs / '3.txt'}")
    assert prompt.index(f"2. {workspace.jobs / '3.txt'}") < prompt.index(f"3. {workspace.jobs / '11.txt'}")


def test_prepare_default_workspace_keeps_next_command_short(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_prepare(_memorize_input: Any, workspace: Any, _backend: Any, **_kwargs: Any) -> Any:
        return _prepared(workspace, ())

    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(_payload())))
    monkeypatch.setattr(cli, "_build_backend", lambda _args: object())
    monkeypatch.setattr(cli, "prepare_memorize", fake_prepare)

    assert cli.main(["memorize", "prepare", "-", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["next_command"] == "memu memorize commit"


def test_prepare_missing_file_reports_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["memorize", "prepare", "/definitely/not/input.json"]) == 2
    assert "no such file" in capsys.readouterr().err


def test_prepare_rejects_more_than_ten_payloads(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["memorize", "prepare", *("-" for _ in range(11))]) == 2
    assert "at most 10" in capsys.readouterr().err


def test_prepare_invalid_input_reports_validation_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = tmp_path / "invalid.json"
    payload.write_text(json.dumps({"items": []}), encoding="utf-8")

    assert cli.main(["memorize", "prepare", str(payload)]) == 1
    assert "at least 1 item" in capsys.readouterr().err


def test_commit_uses_selected_backend_and_fixed_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "workspace"
    backend = object()
    received: dict[str, Any] = {}

    async def fake_commit(selected_workspace: Any, selected_backend: Any) -> dict[str, Any]:
        received.update({"workspace": selected_workspace, "backend": selected_backend})
        return {
            "recall_files": [{"track": "memory", "name": "profile"}],
            "resources": [{"url": "/workspace/notes.md"}],
        }

    monkeypatch.setattr(cli, "MEMORIZE_WORKSPACE", str(workspace))
    monkeypatch.setattr(cli, "_build_backend", lambda _args: backend)
    monkeypatch.setattr(cli, "commit_memorize", fake_commit)

    assert cli.main(["memorize", "commit"]) == 0
    assert received == {"workspace": cli.MemorizeWorkspace(workspace), "backend": backend}
    output = capsys.readouterr().out
    assert "committed 1 recall file(s) and 1 resource(s)" in output
    assert "memory/profile" in output


def test_verify_resources_uses_fixed_workspace_without_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "workspace"
    received: tuple[Path, Path] | None = None

    def fake_verify(log: Path, resources: Path) -> int:
        nonlocal received
        received = (log, resources)
        return 2

    monkeypatch.setattr(cli, "MEMORIZE_WORKSPACE", str(workspace))
    monkeypatch.setattr(cli, "verify_resource_log", fake_verify)
    monkeypatch.setattr(cli, "_build_backend", lambda _args: pytest.fail("verifier must not build a backend"))

    assert cli.main(["memorize", "verify-resources"]) == 0
    assert received == (workspace / ".resource.tmp", workspace / "resources.md")
    assert "verified 2 resource(s)" in capsys.readouterr().out
