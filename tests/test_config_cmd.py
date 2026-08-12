"""``init`` and ``config`` — the commands that write ``config.env`` (ADR 0017).

Weighted toward the two properties that make writing this file by command better
than writing it by prose: **the merge never loses a line**, and **the guard never
lets one backend's memory be stranded by a switch to the other**. A verb that
sets the right key is table stakes; one that takes another host's settings with
it, or that flips a configured store because a shell happened to export a
variable, is the failure this replaced.
"""

from __future__ import annotations

import codecs
import locale
import os
import pathlib

import pytest

from memu import config_file
from memu import env as env_module
from memu.hosts.claude_code.cli import SPEC
from memu.hosts.host_cli import run


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    """An isolated ``config.env`` path (not yet created). Returns it."""
    from memu import env as env_module

    path = tmp_path / "memu" / "config.env"
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(path))
    # The dotenv loader is process-cached, and these commands write through it.
    env_module.reload()
    for key in ("MEMU_MEMORY_MODE", "MEMU_DB", "MEMU_CLOUD_API_KEY", "MEMU_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)
    return path


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# The writer
# --------------------------------------------------------------------------- #


def test_merge_leaves_every_other_line_untouched(config: pathlib.Path) -> None:
    """The field failure this command exists to end: a rewrite that takes
    another host's settings, and the user's comments, with it."""
    _write(
        config,
        "# written by hand in 2024\nMEMU_DB=/srv/memu.sqlite3\n\nMEMU_EMBED_PROVIDER=jina\nNO_PROXY=localhost\n",
    )

    config_file.write_values({"MEMU_MEMORY_MODE": "local"})

    assert config.read_text(encoding="utf-8") == (
        "# written by hand in 2024\n"
        "MEMU_DB=/srv/memu.sqlite3\n"
        "\n"
        "MEMU_EMBED_PROVIDER=jina\n"
        "NO_PROXY=localhost\n"
        "MEMU_MEMORY_MODE=local\n"
    )


def test_existing_key_is_rewritten_in_place(config: pathlib.Path) -> None:
    """In place, so a key keeps the comment that explains it — appending a second
    assignment would resolve correctly and read as a contradiction."""
    _write(config, "# the store\nMEMU_DB=/old\n# the endpoint\nMEMU_BASE_URL=http://localhost:11434/v1\n")

    config_file.write_values({"MEMU_DB": "/new"})

    assert config.read_text(encoding="utf-8") == (
        "# the store\nMEMU_DB=/new\n# the endpoint\nMEMU_BASE_URL=http://localhost:11434/v1\n"
    )


def test_duplicate_assignments_all_collapse_to_the_new_value(config: pathlib.Path) -> None:
    """Two first runs racing to append ``MEMU_CLIENT_ID`` is the real case. The
    parser takes the last, so an untouched earlier line would preserve a value
    that no longer resolves."""
    _write(config, "MEMU_CLIENT_ID=one\nMEMU_DB=/srv/db\nMEMU_CLIENT_ID=two\n")

    config_file.write_values({"MEMU_CLIENT_ID": "three"})

    assert config.read_text(encoding="utf-8") == "MEMU_CLIENT_ID=three\nMEMU_DB=/srv/db\nMEMU_CLIENT_ID=three\n"
    assert config_file.read()["MEMU_CLIENT_ID"] == "three"


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits only")
def test_file_is_owner_only(config: pathlib.Path) -> None:
    config_file.write_values({"MEMU_CLOUD_API_KEY": "sk-secret"})

    assert config.stat().st_mode & 0o777 == 0o600
    assert config.parent.stat().st_mode & 0o077 == 0


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits only")
def test_nothing_to_set_still_restricts_an_existing_file(config: pathlib.Path) -> None:
    _write(config, "MEMU_DB=/srv/db\n")
    config.chmod(0o644)

    _, changed = config_file.write_values({})

    assert changed is False
    assert config.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(os.name != "nt", reason="Windows permission behavior only")
def test_windows_write_inherits_acls_without_chmod(config: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chmod_calls: list[int] = []
    monkeypatch.setattr(pathlib.Path, "chmod", lambda _path, mode: chmod_calls.append(mode))

    path, changed = config_file.write_values({"MEMU_CLOUD_API_KEY": "sk-secret"})

    assert (path, changed) == (config, True)
    assert config_file.read()["MEMU_CLOUD_API_KEY"] == "sk-secret"
    assert chmod_calls == []
    assert config_file.permission_note() == "plaintext key; Windows ACLs inherited"


def test_read_is_blind_to_the_process_environment(config: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The distinction the whole guard rests on. ``env.env()`` resolves the shell
    first — correct for "what is this run using", wrong for "what is on disk"."""
    _write(config, "MEMU_DB=/srv/db\n")
    monkeypatch.setenv("MEMU_CLOUD_API_KEY", "sk-from-the-shell")

    assert "MEMU_CLOUD_API_KEY" not in config_file.read()


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16-le", "utf-16-be"])
def test_init_migrates_a_bom_encoded_config_to_utf8(config: pathlib.Path, encoding: str) -> None:
    text = "# 用户配置\nMEMU_DB=C:/用户/memu.sqlite3\n"
    codecs_by_encoding = {
        "utf-8-sig": codecs.BOM_UTF8 + text.encode("utf-8"),
        "utf-16-le": codecs.BOM_UTF16_LE + text.encode("utf-16-le"),
        "utf-16-be": codecs.BOM_UTF16_BE + text.encode("utf-16-be"),
    }
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_bytes(codecs_by_encoding[encoding])
    env_module.reload()

    assert env_module.env("MEMU_DB") == "C:/用户/memu.sqlite3"
    assert run(SPEC, ["init"]) == 0

    migrated = config.read_bytes()
    assert not migrated.startswith((codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    assert migrated.decode("utf-8").splitlines()[:2] == text.splitlines()
    assert config_file.read()["MEMU_DB"] == "C:/用户/memu.sqlite3"


@pytest.mark.skipif(os.name != "nt", reason="Windows ANSI code page only")
def test_init_migrates_a_windows_ansi_config_to_utf8(config: pathlib.Path) -> None:
    text = "# 用户配置\nMEMU_DB=C:/用户/memu.sqlite3\n"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_bytes(text.encode(locale.getencoding()))
    env_module.reload()

    assert env_module.env("MEMU_DB") == "C:/用户/memu.sqlite3"
    assert run(SPEC, ["init"]) == 0

    assert config.read_bytes().decode("utf-8").splitlines()[:2] == text.splitlines()
    assert config_file.read()["MEMU_DB"] == "C:/用户/memu.sqlite3"


def test_no_logical_update_still_migrates_legacy_encoding(config: pathlib.Path) -> None:
    text = "MEMU_MEMORY_MODE=local\nMEMU_CLIENT_ID=existing\n"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_bytes(codecs.BOM_UTF16_LE + text.encode("utf-16-le"))

    path, changed = config_file.write_values({})

    assert (path, changed) == (config, True)
    assert config.read_bytes().decode("utf-8").splitlines() == text.splitlines()


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #


def test_bare_init_writes_local_and_a_client_id(config: pathlib.Path) -> None:
    assert run(SPEC, ["init"]) == 0

    values = config_file.read()
    assert values["MEMU_MEMORY_MODE"] == "local"
    assert values["MEMU_CLIENT_ID"]


def test_bare_init_keeps_a_declared_cloud_mode(config: pathlib.Path) -> None:
    """A re-install where the user did not re-supply a key must not demote cloud."""
    _write(config, "MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=sk-1\n")

    assert run(SPEC, ["init"]) == 0

    assert config_file.read()["MEMU_MEMORY_MODE"] == "cloud"


def test_bare_init_is_idempotent(config: pathlib.Path) -> None:
    """SKILL.md's mitigation for agents that skip steps is that re-running is
    free, so a second run must not generate a second client id."""
    run(SPEC, ["init"])
    first = config.read_text(encoding="utf-8")

    assert run(SPEC, ["init"]) == 0
    assert config.read_text(encoding="utf-8") == first


def test_init_with_a_key_selects_cloud(config: pathlib.Path) -> None:
    assert run(SPEC, ["init", "--cloud-api-key", "sk-1"]) == 0

    values = config_file.read()
    assert values["MEMU_MEMORY_MODE"] == "cloud"
    assert values["MEMU_CLOUD_API_KEY"] == "sk-1"


def test_init_with_a_key_flips_a_vacuous_local_config(config: pathlib.Path) -> None:
    """The ordinary first install: bare ``init`` landed ``local`` before the guide
    asked the question. An inferred default must not be treated as a choice."""
    run(SPEC, ["init"])

    assert run(SPEC, ["init", "--cloud-api-key", "sk-1"]) == 0
    assert config_file.read()["MEMU_MEMORY_MODE"] == "cloud"


def test_init_with_a_key_flips_a_local_config_with_a_store_and_warns(
    config: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`init` has no ``--force``, so a refusal here is terminal and would halt the
    install at its first step. A key in hand is intent enough, and the store is
    not destroyed — only unread — so the cost is a warning."""
    _write(config, "MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\n")

    assert run(SPEC, ["init", "--cloud-api-key", "sk-1"]) == 0

    assert config_file.read()["MEMU_MEMORY_MODE"] == "cloud"
    # Left alone: the switch is reversible precisely because the store survives it.
    assert config_file.read()["MEMU_DB"] == "/srv/db"
    captured = capsys.readouterr()
    assert "no longer read" in captured.out
    assert "config --local --force" in captured.err


def test_init_never_echoes_the_key_in_its_warning(config: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """It is already in argv, and memU mines the transcript this prints into."""
    _write(config, "MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\n")

    run(SPEC, ["init", "--cloud-api-key", "sk-secret"])

    captured = capsys.readouterr()
    assert "sk-secret" not in captured.err
    assert "sk-secret" not in captured.out


def test_init_with_a_key_does_not_warn_on_a_vacuous_config(
    config: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ordinary first install has nothing to lose, and a warning printed on
    every one of them is a warning nobody reads on the run that matters."""
    run(SPEC, ["init"])
    capsys.readouterr()

    assert run(SPEC, ["init", "--cloud-api-key", "sk-1"]) == 0

    captured = capsys.readouterr()
    assert "no longer read" not in captured.out
    assert "warning" not in captured.err


def test_init_replaces_a_stored_key_and_says_so(config: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Refusing would block the legitimate rotated-key repair, and the client
    cannot tell a rotation from a different account. Announcing is the middle."""
    _write(config, "MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=sk-1\n")

    assert run(SPEC, ["init", "--cloud-api-key", "sk-2"]) == 0

    assert config_file.read()["MEMU_CLOUD_API_KEY"] == "sk-2"
    assert "replaced" in capsys.readouterr().out


def test_init_ignores_a_mode_exported_in_the_shell(config: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ "Already set" is a statement about the file. A shell export must not make
    ``init`` keep a mode nobody ever wrote."""
    monkeypatch.setenv("MEMU_MEMORY_MODE", "cloud")

    assert run(SPEC, ["init"]) == 0

    assert config_file.read()["MEMU_MEMORY_MODE"] == "local"


# --------------------------------------------------------------------------- #
# The one-backend guard
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("existing", "target", "expected"),
    [
        # Protected: the current mode has memory to lose.
        ("MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\n", "--cloud", 2),
        ("MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=sk-1\n", "--local", 2),
        # A legacy file predating MEMU_MEMORY_MODE is *in* local mode, not vacuous —
        # and is the population most likely to hold a large store.
        ("MEMU_DB=/srv/db\n", "--cloud", 2),
        # Vacuous: a declaration with nothing behind it. This is the first real choice.
        ("MEMU_MEMORY_MODE=local\n", "--cloud", 0),
        ("MEMU_MEMORY_MODE=cloud\n", "--local", 0),
        ("", "--cloud", 0),
        # Not a flip at all.
        ("MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\n", "--local", 0),
        ("MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=sk-1\n", "--cloud", 0),
    ],
)
def test_mode_flip_guard(config: pathlib.Path, existing: str, target: str, expected: int) -> None:
    if existing:
        _write(config, existing)

    assert run(SPEC, ["config", target]) == expected


def test_force_overrides_the_flip_guard(config: pathlib.Path) -> None:
    _write(config, "MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\n")

    assert run(SPEC, ["config", "--cloud", "--cloud-api-key", "sk-1", "--force"]) == 0

    assert config_file.read()["MEMU_MEMORY_MODE"] == "cloud"


def test_guard_ignores_a_key_exported_in_the_shell(config: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An exported credential must not make a file that declares nothing look
    like a configured cloud install and refuse the first real choice."""
    _write(config, "MEMU_MEMORY_MODE=cloud\n")
    monkeypatch.setenv("MEMU_CLOUD_API_KEY", "sk-from-the-shell")

    assert run(SPEC, ["config", "--local"]) == 0


@pytest.mark.parametrize("key", ["MEMU_DB", "MEMU_EMBED_PROVIDER", "MEMU_EMBED_MODEL"])
def test_identity_keys_refuse_a_change(config: pathlib.Path, key: str) -> None:
    """These three bind an embedding space. Changing one strands every vector
    already written against it, and retrieval keeps succeeding while finding
    nothing — which is why the guard here is unconditional, not state-based."""
    _write(config, f"MEMU_MEMORY_MODE=local\n{key}=original\n")
    flag = {"MEMU_DB": "--db", "MEMU_EMBED_PROVIDER": "--embed-provider", "MEMU_EMBED_MODEL": "--embed-model"}[key]

    assert run(SPEC, ["config", "--local", flag, "changed"]) == 2
    assert config_file.read()[key] == "original"

    assert run(SPEC, ["config", "--local", flag, "changed", "--force"]) == 0
    assert config_file.read()[key] == "changed"


def test_setting_an_absent_identity_key_is_not_a_change(config: pathlib.Path) -> None:
    _write(config, "MEMU_MEMORY_MODE=local\n")

    assert run(SPEC, ["config", "--local", "--db", "/srv/db"]) == 0


def test_connection_keys_are_freely_updatable(config: pathlib.Path) -> None:
    """ "Repair the connection, never the identity" — the guide's rule, now a gate."""
    _write(config, "MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\nMEMU_BASE_URL=http://localhost:11434/v1\n")

    assert run(SPEC, ["config", "--local", "--embed-base-url", "http://127.0.0.1:11434/v1"]) == 0

    assert config_file.read()["MEMU_BASE_URL"] == "http://127.0.0.1:11434/v1"


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #


def test_config_requires_a_backend(config: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(SPEC, ["config"]) == 2
    assert "config show" in capsys.readouterr().err


def test_config_local_without_a_store_is_allowed(config: pathlib.Path) -> None:
    """The refusal would land in the wrong place: this verb runs inside INSTALL.md,
    where the agent is already talking to the user about the store. Part 1's verify
    gate is what catches a mode with nothing behind it."""
    assert run(SPEC, ["config", "--local"]) == 0

    assert config_file.read()["MEMU_MEMORY_MODE"] == "local"
    assert "MEMU_DB" not in config_file.read()


def test_config_does_not_persist_the_default_endpoint(config: pathlib.Path) -> None:
    """Baking today's default into the file freezes across upgrades a value the
    code should own."""
    from memu.cloud import DEFAULT_CLOUD_BASE_URL

    assert run(SPEC, ["config", "--cloud", "--cloud-api-key", "sk-1", "--cloud-base-url", DEFAULT_CLOUD_BASE_URL]) == 0

    assert "MEMU_CLOUD_BASE_URL" not in config_file.read()


def test_config_persists_a_non_default_endpoint(config: pathlib.Path) -> None:
    assert run(SPEC, ["config", "--cloud", "--cloud-api-key", "sk-1", "--cloud-base-url", "https://staging/api/"]) == 0

    assert config_file.read()["MEMU_CLOUD_BASE_URL"] == "https://staging/api/"


def test_embed_api_key_writes_the_embedding_variable(config: pathlib.Path) -> None:
    """``MEMU_API_KEY`` is the embedding provider's, ``MEMU_CLOUD_API_KEY`` is memU
    Cloud's, and the guides have to warn against confusing them. Neither flag is
    called ``--api-key`` for that reason."""
    assert run(SPEC, ["config", "--local", "--embed-api-key", "sk-embed"]) == 0

    values = config_file.read()
    assert values["MEMU_API_KEY"] == "sk-embed"
    assert "MEMU_CLOUD_API_KEY" not in values


def test_config_only_writes_the_flags_it_was_given(config: pathlib.Path) -> None:
    _write(config, "MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\nMEMU_EMBED_PROVIDER=jina\n")

    assert run(SPEC, ["config", "--local", "--embed-model", "nomic-embed-text"]) == 0

    values = config_file.read()
    assert values["MEMU_DB"] == "/srv/db"
    assert values["MEMU_EMBED_PROVIDER"] == "jina"
    assert values["MEMU_EMBED_MODEL"] == "nomic-embed-text"


# --------------------------------------------------------------------------- #
# config show
# --------------------------------------------------------------------------- #


def test_show_writes_nothing(config: pathlib.Path) -> None:
    """The preflight probe. A read side that created the file would answer its own
    question wrong on every later run."""
    assert run(SPEC, ["config", "show"]) == 0

    assert not config.exists()


def test_show_never_prints_a_credential(config: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(config, "MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=sk-secret\n")

    run(SPEC, ["config", "show"])

    out = capsys.readouterr().out
    assert "sk-secret" not in out
    assert "key       set" in out


def test_show_reports_an_environment_override(
    config: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """This command reports the file, but the environment is what wins at runtime.
    Silence where the two disagree makes a probe into a misleading one."""
    _write(config, "MEMU_MEMORY_MODE=local\nMEMU_DB=/srv/db\n")
    monkeypatch.setenv("MEMU_DB", "/srv/other")

    run(SPEC, ["config", "show"])

    assert "note: the environment overrides" in capsys.readouterr().out


def test_show_names_the_backward_compatible_mode(config: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(config, "MEMU_DB=/srv/db\n")

    run(SPEC, ["config", "show"])

    assert "undeclared" in capsys.readouterr().out
