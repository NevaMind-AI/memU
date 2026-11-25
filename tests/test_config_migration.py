"""Installed-user upgrades preserve settings, identity, rollback data and overrides."""

from __future__ import annotations

import codecs
import os
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor

import pytest

from memu import config_file
from memu import env as config_env
from memu.config_schema import KEYS, env_value, typed_value


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    path = tmp_path / "settings.env"
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(path))
    monkeypatch.delenv("MEMU_CONFIG", raising=False)
    config_env.reload()
    yield path
    config_env.reload()


def test_upgrade_preserves_settings_identity_and_original_bytes(legacy, capsys, monkeypatch):
    monkeypatch.setenv("MEMU_DB", "/temporary/shell/database")
    text = (
        "# 用户配置\nMEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=secret-value\n"
        "MEMU_DB=C:/用户/memory.sqlite3\nMEMU_LLM_PROVIDER=jina\n"
        "MEMU_EMBED_MODEL=custom-model\nMEMU_EMBED_BATCH_SIZE=10\n"
        "MEMU_CLIENT_ID=existing-id\nMEMU_TELEMETRY=0\n"
        "MEMU_CLOUD_RETRIEVE_MIN_SCORE_LONG=0.71\n"
        "MEMU_EVENTS_BASE_URL=\nCUSTOM_SETTING=preserved\n"
    )
    original = codecs.BOM_UTF16_LE + text.encode("utf-16-le")
    legacy.write_bytes(original)
    values = config_file.read()
    target = config_file.config_path()
    document = tomllib.loads(target.read_text(encoding="utf-8"))
    assert document["cloud"]["api_key"] == "secret-value"
    assert document["local"]["db"] == "C:/用户/memory.sqlite3"
    assert document["embedding"]["provider"] == "jina"
    assert document["embedding"]["batch_size"] == 10
    assert document["telemetry"]["enabled"] is False
    assert document["telemetry"]["base_url"] == ""
    assert document["retrieval"]["cloud"]["min_score"]["long"] == 0.71
    assert document["legacy"]["CUSTOM_SETTING"] == "preserved"
    assert values["MEMU_CLIENT_ID"] == "existing-id"
    assert "client_id" not in document
    assert legacy.read_bytes() == original
    assert config_env.env("MEMU_DB") == "/temporary/shell/database"
    assert config_env.env_declared("MEMU_EVENTS_BASE_URL", "default") == ""
    assert "secret-value" not in capsys.readouterr().err
    before = target.read_bytes(), target.stat().st_mtime_ns
    assert config_file.read() == values
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before


def test_existing_toml_is_authoritative_and_merges_preserve_comments(legacy):
    legacy.write_text("MEMU_DB=/old\n")
    target = config_file.config_path()
    original = '# user comment\n[local]\ndb = "/new" # keep here\n\n[custom]\nvalue = 3\n'
    target.write_text(original)
    assert config_file.read()["MEMU_DB"] == "/new"
    config_file.write_values({"MEMU_DB": "/edited"})
    text = target.read_text()
    assert 'db = "/edited" # keep here' in text
    assert "# user comment" in text
    assert tomllib.loads(text)["custom"] == {"value": 3}
    assert legacy.read_text() == "MEMU_DB=/old\n"


@pytest.mark.parametrize("failure", ["validation", "replace"])
def test_failed_migration_falls_back_without_secret_output(legacy, monkeypatch, capsys, failure):
    text = "MEMU_CLOUD_API_KEY=keep-secret\nMEMU_DB=/keep\n"
    if failure == "validation":
        text += "MEMU_EMBED_BATCH_SIZE=invalid-secret\n"
    else:

        def fail_replace(*args):
            raise OSError("keep-secret")

        monkeypatch.setattr(config_file.os, "replace", fail_replace)
    legacy.write_text(text)
    assert config_file.read()["MEMU_DB"] == "/keep"
    assert legacy.read_text() == text
    assert not config_file.config_path().exists()
    assert not list(legacy.parent.glob(".settings.toml.*"))
    output = capsys.readouterr().err
    assert "migration failed" in output
    assert "secret" not in output


def test_invalid_new_file_is_not_silently_replaced_by_legacy(legacy):
    legacy.write_text("MEMU_DB=/old\n")
    target = config_file.config_path()
    target.write_text("[local]\ndb = 123\n")
    with pytest.raises(ValueError, match=r"local\.db"):
        config_file.read()
    assert target.read_text() == "[local]\ndb = 123\n"


def test_custom_target_and_concurrent_processes(legacy, tmp_path, monkeypatch):
    legacy.write_text("MEMU_DB=/shared\nMEMU_CLIENT_ID=stable\n")
    target = tmp_path / "custom" / "memory.toml"
    monkeypatch.setenv("MEMU_CONFIG", str(target))
    script = "from memu.config_file import read; v=read(); assert v['MEMU_DB']=='/shared'; assert v['MEMU_CLIENT_ID']=='stable'"

    def worker(_):
        return subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=20, check=False)  # noqa: S603

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, range(4)))
    assert all(result.returncode == 0 for result in results), [r.stderr.decode() for r in results]
    assert sum(b"; original file retained" in r.stderr for r in results) == 1
    assert tomllib.loads(target.read_text())["local"]["db"] == "/shared"
    assert config_file.read()["MEMU_CLIENT_ID"] == "stable"


def test_all_public_keys_round_trip_through_typed_toml(legacy):
    values = dict.fromkeys(KEYS, "text")
    for key in values:
        if "_MIN_SCORE_" in key:
            values[key] = "0.61"
    values.update(
        MEMU_MEMORY_MODE="local",
        MEMU_EMBED_BATCH_SIZE="7",
        MEMU_QUERY_EXTRACT_ENABLED="true",
        MEMU_TELEMETRY="false",
        MEMU_DEBUG="true",
        MEMU_EVENTS_DEBUG="false",
        MEMU_COWORK_ROOTS=os.pathsep.join(["/first", "/second"]),
    )
    legacy.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    loaded = config_file.read()
    for key, value in values.items():
        assert loaded[key] == env_value(key, typed_value(key, value))


@pytest.mark.parametrize("modern", ["", "MEMU_EMBED_PROVIDER=\n"])
def test_legacy_provider_alias_and_shell_override(legacy, monkeypatch, modern):
    legacy.write_text("MEMU_LLM_PROVIDER=jina\n" + modern)
    assert config_file.read()["MEMU_EMBED_PROVIDER"] == "jina"
    monkeypatch.setenv("MEMU_LLM_PROVIDER", "voyage")
    assert config_env.embedding_provider() == "voyage"


def test_advanced_toml_settings_reach_their_consumers(legacy, tmp_path, monkeypatch):
    from memu import events
    from memu.hosts import templates
    from memu.hosts.cowork.sessions import platform_data_roots

    for key in ("MEMU_COWORK_ROOTS", "MEMU_DOCS_BASE_URL", "MEMU_TEMPLATE_BASE_URL", "MEMU_EVENTS_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    config_file.write_values({
        "MEMU_COWORK_ROOTS": str(tmp_path),
        "MEMU_DOCS_BASE_URL": "",
        "MEMU_TEMPLATE_BASE_URL": "",
        "MEMU_EVENTS_BASE_URL": "",
    })
    config_env.reload()
    assert platform_data_roots() == [tmp_path.resolve()]
    assert templates._base_url() is None
    assert templates._docs_base_url() is None
    assert events.events_url() is None


def test_concurrent_configuration_writes_merge_distinct_keys(legacy):
    config_file.write_values({"MEMU_DB": "/same-store"})
    updates = [{"MEMU_EMBED_MODEL": "model"}, {"MEMU_API_KEY": "key"}, {"MEMU_HTTP_PROXY": "http://proxy"}]
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(config_file.write_values, updates))
    values = config_file.read()
    for update in updates:
        for key, value in update.items():
            assert values[key] == value
    assert values["MEMU_DB"] == "/same-store"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_config_and_state_are_owner_only(legacy):
    legacy.write_text("MEMU_CLIENT_ID=stable\nMEMU_CLOUD_API_KEY=secret\n")
    config_file.read()
    for path in (config_file.config_path(), config_file.state_path()):
        assert path.stat().st_mode & 0o777 == 0o600
