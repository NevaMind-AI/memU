"""Self-updating templates: server first, last-good cache next, embedded last.

These pin the properties the feature rests on: a server typo can never crash the
pipeline (validation), a *transient* outage keeps the last good copy instead of
regressing to embedded (the cache), and the retrieve procedure's scheduled
refresh skips rather than downgrades when the server is unreachable.
"""

from __future__ import annotations

import pathlib

import pytest

from memu.hosts import instruction, templates

BINARY = "memu-codex"

MEMORY_KEYS = "{input_path} {track_dir}"  # the memory-job template's required placeholders


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self, n: int = -1) -> bytes:
        return self._body if n < 0 else self._body[:n]

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _serve(monkeypatch: pytest.MonkeyPatch, body: bytes, status: int = 200) -> None:
    monkeypatch.setenv("MEMU_TEMPLATE_BASE_URL", "https://example.test/inst")
    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout=None: _FakeResponse(body, status))


def _server_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_TEMPLATE_BASE_URL", "https://example.test/inst")

    def _boom(url: str, timeout: float | None = None) -> _FakeResponse:
        raise OSError

    monkeypatch.setattr("urllib.request.urlopen", _boom)


# --- validation: a bad server copy is rejected, never carried into a job ---


def test_valid_accepts_a_well_formed_template() -> None:
    assert templates._valid(f"do the thing {MEMORY_KEYS}", {"input_path", "track_dir"})


@pytest.mark.parametrize(
    "text",
    [
        "",  # empty
        "only {input_path} here",  # a required placeholder is missing
        f"lone }} brace {MEMORY_KEYS}",  # would raise ValueError at .format()
        f"{{unknown}} field {MEMORY_KEYS}",  # references a key the SDK never supplies
    ],
)
def test_valid_rejects_malformed_templates(text: str) -> None:
    assert not templates._valid(text, {"input_path", "track_dir"})


# --- fetch: validated server copy, or None; a good fetch refreshes the cache ---


def test_fetch_returns_and_caches_a_valid_server_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    body = f"server memory job {MEMORY_KEYS}"
    _serve(monkeypatch, body.encode())

    assert templates.fetch(templates.MEMORY_JOB) == body
    assert (templates._cache_dir() / f"{templates.MEMORY_JOB}.txt").read_text(encoding="utf-8") == body


def test_fetch_is_off_when_base_url_is_blank() -> None:
    # The conftest default: no network, so no fetch and no cache write.
    assert templates.fetch(templates.MEMORY_JOB) is None


@pytest.mark.parametrize(
    "body, status",
    [
        pytest.param(f"server {MEMORY_KEYS}".encode(), 404, id="non-200"),
        pytest.param(b"x" * (templates._MAX_BYTES + 1), 200, id="oversize"),
        pytest.param(b"missing the placeholders", 200, id="malformed"),
    ],
    ids=("non-200", "oversize", "malformed"),
)
def test_fetch_rejects_bad_responses_without_caching(monkeypatch: pytest.MonkeyPatch, body: bytes, status: int) -> None:
    _serve(monkeypatch, body, status)

    assert templates.fetch(templates.MEMORY_JOB) is None
    assert not (templates._cache_dir() / f"{templates.MEMORY_JOB}.txt").exists()


# --- resolve: the whole point — a transient outage keeps last-good, not embedded ---


def test_resolve_prefers_the_last_good_cache_over_embedded_on_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    embedded = f"embedded v0 {MEMORY_KEYS}"
    remote_v1 = f"server v1 {MEMORY_KEYS}"

    _serve(monkeypatch, remote_v1.encode())
    assert templates.resolve(templates.MEMORY_JOB, embedded) == remote_v1  # seen once, now cached

    _server_down(monkeypatch)  # the next day the pull fails
    assert templates.resolve(templates.MEMORY_JOB, embedded) == remote_v1, (
        "a transient outage must keep the last-good v1, not regress to the embedded v0"
    )


def test_resolve_falls_to_embedded_with_no_cache_and_no_server(monkeypatch: pytest.MonkeyPatch) -> None:
    embedded = f"embedded floor {MEMORY_KEYS}"
    _server_down(monkeypatch)

    assert templates.resolve(templates.MEMORY_JOB, embedded) == embedded


def test_resolve_ignores_a_corrupt_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = templates._cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{templates.MEMORY_JOB}.txt").write_text("corrupt } cache", encoding="utf-8")
    embedded = f"embedded floor {MEMORY_KEYS}"
    _server_down(monkeypatch)

    assert templates.resolve(templates.MEMORY_JOB, embedded) == embedded


# --- refresh: the installed file is the retrieval skill's last-good, so skip on failure ---


def _skill(body: str) -> bytes:
    """A full SKILL.md document, as the server now serves it — frontmatter,
    heading, and body — wrapping ``body`` (which may carry ``{binary}``)."""
    return (
        f"---\nname: memu-retrieve\ndescription: Retrieve durable memory from memU.\n---\n\n"
        f"# Retrieve from memU before answering\n\n{body}\n"
    ).encode()


def test_refresh_updates_the_installed_skill_from_the_server(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    skills = tmp_path / "skills"
    instruction.install_skill(skills, BINARY)  # embedded, as install-instruction would
    _serve(monkeypatch, _skill("Fresh retrieval body: run {binary} retrieve."))

    touched = instruction.refresh(tmp_path / "AGENTS.md", BINARY, skills_dir=skills)

    text = (skills / instruction.SKILL_NAME / "SKILL.md").read_text(encoding="utf-8")
    assert touched == [(instruction.skill_path(skills), True)]
    # The server's full document lands verbatim, with only {binary} filled.
    assert text.startswith("---\nname: memu-retrieve\n")
    assert "Fresh retrieval body: run memu-codex retrieve." in text


def test_refresh_skips_and_does_not_downgrade_when_server_is_down(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    skills = tmp_path / "skills"
    # A newer skill is already installed (as a prior successful refresh would leave it).
    instruction.install_skill(skills, BINARY, skill_text=_skill("Installed v1 body: run {binary} retrieve.").decode())
    installed = (skills / instruction.SKILL_NAME / "SKILL.md").read_text(encoding="utf-8")
    _server_down(monkeypatch)

    touched = instruction.refresh(tmp_path / "AGENTS.md", BINARY, skills_dir=skills)

    assert touched == []
    assert (skills / instruction.SKILL_NAME / "SKILL.md").read_text(encoding="utf-8") == installed


def test_refresh_does_not_bootstrap_an_uninstalled_skill(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    skills = tmp_path / "skills"
    _serve(monkeypatch, _skill("Fresh retrieval body: run {binary} retrieve."))

    touched = instruction.refresh(tmp_path / "AGENTS.md", BINARY, skills_dir=skills)

    assert touched == []
    assert not (skills / instruction.SKILL_NAME / "SKILL.md").exists()


def test_refresh_updates_an_inline_host_in_place(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")
    instruction.install(path, BINARY)  # inline host: full body in the managed block
    _serve(monkeypatch, _skill("Inline refreshed body: run {binary} retrieve."))

    touched = instruction.refresh(path, BINARY, skills_dir=None)

    text = path.read_text(encoding="utf-8")
    assert touched == [(path, True)]
    # Only the body is carved into the inline block — no frontmatter, no skill heading.
    assert "Inline refreshed body: run memu-codex retrieve." in text
    assert "name: memu-retrieve" not in text
    assert "# Retrieve from memU before answering" not in text
    assert "# My rules" in text, "the user's own content survives the refresh"
