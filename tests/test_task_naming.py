"""One task-name source feeds every scheduler guide and lifecycle."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from memu.hosts import templates
from memu.hosts.claude_code.cli import SPEC as CLAUDE
from memu.hosts.codex.cli import SPEC as CODEX
from memu.hosts.cola.cli import SPEC as COLA
from memu.hosts.cursor.cli import SPEC as CURSOR
from memu.hosts.generic.cli import SPEC as GENERIC
from memu.hosts.hermes.cli import SPEC as HERMES
from memu.hosts.host_cli import DOCS, HostSpec
from memu.hosts.openclaw.cli import SPEC as OPENCLAW
from memu.hosts.workbuddy.cli import SPEC as WORKBUDDY

SPECS = (CLAUDE, CURSOR, HERMES, CODEX, OPENCLAW, WORKBUDDY, COLA, GENERIC)


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: spec.host)
@pytest.mark.parametrize("filename", DOCS.values())
def test_embedded_docs_render_names_only_from_host_spec(spec: HostSpec, filename: str) -> None:
    source = (files(spec.package) / filename).read_text(encoding="utf-8")
    if spec.host == "codex" and filename == "BRIDGING_TASK.md":
        assert source == ""
        return

    assert templates._valid_doc(source)
    assert "{{task_name}}" in source
    assert "{{former_task_names}}" in source
    assert "{{all_task_names}}" in source
    assert all(name not in source for name in spec.all_task_names), "task-name literals belong only in HostSpec"
    if filename == "BRIDGING_TASK.md":
        assert source.startswith("---\nname: {{task_doc_name}}\n")

    rendered = spec.render_doc(source)
    assert spec.task_name in rendered
    assert all(name in rendered for name in spec.former_task_names)
    assert "{{" not in rendered and "}}" not in rendered
    if filename == "BRIDGING_TASK.md":
        assert rendered.startswith(f"---\nname: {spec.task_doc_name}\n")


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: spec.host)
def test_task_doc_frontmatter_is_derived_from_current_name(spec: HostSpec) -> None:
    assert spec.task_doc_name == f"create-{spec.task_name}-task"


def test_host_doc_renderer_rejects_unknown_or_unclosed_tokens() -> None:
    with pytest.raises(ValueError, match="unknown host-doc token"):
        CLAUDE.render_doc("{{something_else}}")
    with pytest.raises(ValueError, match="unresolved host-doc token"):
        CLAUDE.render_doc("{{task_name}")


def test_remote_doc_without_naming_contract_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "https://example.test/docs")
    monkeypatch.setattr(templates, "_get", lambda url: "# Old guide\nUse `memu-remember`.\n")

    assert templates.fetch_doc("codex", "BRIDGING_TASK.md") is None


def test_valid_remote_doc_is_cached_then_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (
        "---\nname: {{task_doc_name}}\ndescription: test\n---\n"
        "<!-- memu-codex-record: notify-v2 -->\n"
        "<!-- memu-codex-permissions: v6 -->\n"
        "Current {{task_name}}; former {{former_task_names}}; all {{all_task_names}}.\n"
    )
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "https://example.test/docs")
    monkeypatch.setattr(templates, "_get", lambda url: source)

    resolved = templates.resolve_doc(CODEX.host, "INSTALL.md", "unused")

    assert CODEX.task_name in CODEX.render_doc(resolved)
    assert (templates._docs_cache_dir(CODEX.host) / "INSTALL.md").read_text(encoding="utf-8") == source


@pytest.mark.parametrize("filename", ("INSTALL.md", "UNINSTALL.md"))
def test_codex_record_guides_reject_old_remote_and_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    embedded = (files(CODEX.package) / filename).read_text(encoding="utf-8")
    old = "Current {{task_name}}; former {{former_task_names}}; all {{all_task_names}}.\nCreate a scheduled task.\n"
    if filename == "INSTALL.md":
        old = "<!-- memu-codex-record: notify-v2 -->\n" + old
    cache = tmp_path / filename
    cache.write_text(old, encoding="utf-8")
    monkeypatch.setattr(templates, "_docs_cache_dir", lambda _: tmp_path)
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "https://example.test/docs")
    monkeypatch.setattr(templates, "_get", lambda _: old)

    assert templates._valid_doc(old)  # Naming tokens alone cannot detect the old flow.
    assert templates.resolve_doc("codex", filename, embedded) == embedded
    assert cache.read_text(encoding="utf-8") == old

    monkeypatch.setattr(templates, "_get", lambda _: embedded)
    assert templates.resolve_doc("codex", filename, "unused") == embedded
    assert cache.read_text(encoding="utf-8") == embedded
    monkeypatch.setattr(templates, "_get", lambda _: None)
    assert templates.resolve_doc("codex", filename, "unused") == embedded


def test_codex_task_guide_stays_empty_without_remote_or_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from memu.hosts.codex.cli import main

    assert (files(CODEX.package) / "BRIDGING_TASK.md").read_bytes() == b""
    cache = tmp_path / "BRIDGING_TASK.md"
    old = "Current {{task_name}}; former {{former_task_names}}; all {{all_task_names}}.\nCreate a recurring task.\n"
    cache.write_text(old, encoding="utf-8")
    monkeypatch.setattr(templates, "_docs_cache_dir", lambda _: tmp_path)

    def unexpected_fetch(_url: str) -> str:
        pytest.fail("A disabled guide must not fetch remote instructions")

    monkeypatch.setattr(templates, "_get", unexpected_fetch)
    assert main(["docs", "task"]) == 0
    assert capsys.readouterr().out.strip() == ""
    assert cache.read_text(encoding="utf-8") == old


def test_record_guide_version_guard_is_codex_only() -> None:
    old = "Current {{task_name}}; former {{former_task_names}}; all {{all_task_names}}."
    assert templates._valid_host_doc("claude-code", "INSTALL.md", old)
    assert not templates._valid_host_doc("codex", "INSTALL.md", old)


def test_codex_install_separates_setup_from_legacy_cleanup() -> None:
    text = (files(CODEX.package) / "INSTALL.md").read_text(encoding="utf-8")
    setup, migration = text.split("## Existing installations — migration", 1)
    assert "memu-codex install-hook" in setup
    assert "https://chatgpt.com/codex/install.ps1 | iex" in setup
    assert "https://chatgpt.com/codex/install.sh | sh" in setup
    assert "CODEX_INSTALL_DIR" in setup and "stale PATH" in setup
    assert "hooks/list" in setup and "trusted_hash" in setup
    assert "memu-codex remove-instruction" not in setup
    assert "### M4 — Remove the old retrieve skill" in migration
    assert "~/.codex/skills/memu-retrieve/SKILL.md" in migration
    assert "memu-codex remove-instruction --dry-run" in migration
    assert "memu-codex remove-instruction" in migration
    assert "docs task" not in text
    assert not templates._valid_host_doc("codex", "INSTALL.md", text.replace("notify-v2", "notify-v1"))


def test_codex_install_checks_session_permissions_before_hook_edits() -> None:
    text = (files(CODEX.package) / "INSTALL.md").read_text(encoding="utf-8")
    permissions = text.split("## Execution permissions", 1)[1].split("## Choose the installation path", 1)[0]
    assert "Continue only with `danger-full-access`" in permissions
    assert 'reply "continue installation"' in permissions
    assert "remain paused at" in permissions and "stage 1" in permissions
    assert "Do not rerun an unchanged failing command" in permissions
    skill = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")
    gate = skill.split("## Before installing — Codex permissions", 1)[1].split("## Step 1", 1)[0]
    assert "Continue only when the mode is `danger-full-access`" in gate
    assert "before" in gate and "running `init`" in gate
    assert "Stay in this conversation" in gate
    assert "switch back to their previous permission mode" in skill
    assert "registration-time retrieval below" in skill
    for guide, progress_heading in (
        (skill, "## Codex installation progress"),
        (text, "## Installation progress — five stages"),
    ):
        language = guide.split("## Before installing — choose the guide language", 1)[1].split(progress_heading, 1)[0]
        assert "1. EN — English" in language
        assert "2. ZH — 中文" in language
        assert "3. Other" in language
        assert "End the response immediately after the question and wait for the answer" in language
        assert "do not check or discuss permissions" in language
        assert "reproduce the following prompt exactly, without a preface" in language
        assert "Full access check" in language
        assert "without asking again" in language or "without\nasking again" in language
        assert guide.index("## Before installing — choose the guide language") < guide.index(progress_heading)
    for progress in (
        "🔐 [1/5]",
        "📦 [2/5]",
        "🔔 [3/5]",
        "🧠 [4/5]",
        "🚀 [5/5]",
        "✅ memU installation complete",
    ):
        assert progress in skill and progress in text
    startup = text.split("### ✅ Verify Part 2", 1)[1].split("## Part 3", 1)[0]
    assert "at most 15 seconds" in startup
    assert "do not tail" in startup
    assert "exact local log path" in startup
    assert "Do not wait for" in startup
    migration = text.split("### M2", 1)[1].split("### Migration recovery", 1)[0]
    assert "If no old schedules" in migration
    assert "after this startup check passes" in migration
    assert "wait for the new worker's" in migration
    preflight = text.split("### 3.0 Preflight", 1)[1].split("### 3.1 Register the command", 1)[0]
    assert "state_5.sqlite" in preflight and "-wal" in preflight and "-shm" in preflight
    assert "keeps stdin open" in preflight and '"experimentalApi": true' in preflight
    assert '"clientInfo": {"name": "memu-install", "version": "1"}' in preflight
    assert "do not edit the hook or trust state while this gate fails" in preflight
    assert not templates._valid_host_doc(
        "codex",
        "INSTALL.md",
        text.replace("<!-- memu-codex-permissions: v6 -->", "<!-- memu-codex-permissions: v1 -->"),
    )
