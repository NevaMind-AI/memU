"""Generated recall jobs carry the prose format required for independent recall."""

from pathlib import Path

from memu.hosts.bridging.instructions import prepare_instruction_jobs


def test_generated_jobs_require_contextual_prose(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    prepare_instruction_jobs(
        job_dir=jobs,
        session_dir=tmp_path / "sessions",
        memory_dir=tmp_path / "memory",
        skill_dir=tmp_path / "skill",
        resource_log=tmp_path / ".resource.tmp",
        num_sessions=1,
    )
    memory = (jobs / "1.txt").read_text(encoding="utf-8")
    skill = (jobs / "2.txt").read_text(encoding="utf-8")
    for job in (memory, skill):
        assert "not Markdown tables" in job
        assert "rather than adding table rows" in job
        assert "Preserve unrelated existing content" in job
    assert "one physical\nline" in memory
    assert "include its subject" in memory
    assert "date, scope, or condition" in memory
    assert "condition, action, and outcome" in skill
