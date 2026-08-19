"""One task-name source feeds every scheduler guide and lifecycle."""

from __future__ import annotations

from importlib.resources import files

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
        "Current {{task_name}}; former {{former_task_names}}; all {{all_task_names}}.\n"
    )
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "https://example.test/docs")
    monkeypatch.setattr(templates, "_get", lambda url: source)

    resolved = templates.resolve_doc(CODEX.host, "BRIDGING_TASK.md", "unused")

    assert CODEX.render_doc(resolved).startswith(f"---\nname: {CODEX.task_doc_name}\n")
    assert (templates._docs_cache_dir(CODEX.host) / "BRIDGING_TASK.md").read_text(encoding="utf-8") == source
