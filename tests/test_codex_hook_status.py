import json
import os
from datetime import datetime

from memu.hosts.codex.cli import main


def test_hook_status_filters_by_start_time_and_reports_only_metadata(tmp_path, capsys):
    since = datetime(2026, 1, 2).timestamp()
    for kind in ("retrieve", "memorize"):
        folder = tmp_path / "log" / "hooks" / kind
        folder.mkdir(parents=True)
        old = folder / "2026-01-01_00-00-00.000000-1.log"
        old.write_text("=== START codex pid=1 ===\n", encoding="utf-8")
        os.utime(old, (since + 999, since + 999))
    argv = ["hook-status", "--base-dir", str(tmp_path), "--since", str(since)]
    assert main(argv) == 2
    assert json.loads(capsys.readouterr().out)["memorize"]["log"] is None
    retrieval = tmp_path / "log/hooks/retrieve/2026-01-02_00-00-01.000000-2.log"
    retrieval.write_text(
        json.dumps({
            "hook": "UserPromptSubmit",
            "status": "context_returned",
            "retrieve_exit_code": 0,
            "secret": "PRIVATE",
        })
        + "\n{",
        encoding="utf-8",
    )
    notify = tmp_path / "log/hooks/memorize/2026-01-02_00-00-02.000000-3.log"
    notify.write_text(
        "[2026-01-02 00:00:02+0800] === WORKER codex pid=3 ===\n=== MEMORIZE status=started ===\nPRIVATE\n",
        encoding="utf-8",
    )
    assert main(argv) == 0
    output = capsys.readouterr().out
    assert "PRIVATE" not in output
    assert json.loads(output)["memorize"] == {"status": "started", "log": str(notify)}
    retrieval.write_text('{"hook":"UserPromptSubmit","status":"failed","retrieve_exit_code":1}\n', encoding="utf-8")
    assert main(argv) == 1
