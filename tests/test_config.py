"""config モジュールのテスト."""

import json
import os
from pathlib import Path

import pytest

from papycli.config import (
    get_apis_dir,
    get_conf_dir,
    get_conf_path,
    get_default_api,
    get_logfile,
    load_conf,
    register_api,
    remove_api,
    save_conf,
    set_default_api,
    set_logfile,
    unset_logfile,
)


def test_get_conf_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PAPYCLI_CONF_DIR", raising=False)
    assert get_conf_dir() == Path.home() / ".papycli"


def test_get_conf_dir_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    assert get_conf_dir() == tmp_path


def test_get_conf_path(tmp_path: Path) -> None:
    assert get_conf_path(tmp_path) == tmp_path / "papycli.conf"


def test_get_apis_dir(tmp_path: Path) -> None:
    assert get_apis_dir(tmp_path) == tmp_path / "apis"


def test_load_conf_not_found(tmp_path: Path) -> None:
    assert load_conf(tmp_path) == {}


def test_save_and_load_conf(tmp_path: Path) -> None:
    conf: dict = {"default": "myapi", "myapi": {"url": "http://example.com"}}
    save_conf(conf, tmp_path)
    loaded = load_conf(tmp_path)
    assert loaded == conf


def test_save_conf_creates_dir(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    conf: dict = {"default": "x"}
    save_conf(conf, nested)
    assert (nested / "papycli.conf").exists()


def test_save_conf_file_is_valid_json(tmp_path: Path) -> None:
    conf: dict = {"default": "api1"}
    save_conf(conf, tmp_path)
    raw = (tmp_path / "papycli.conf").read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed == conf


def test_register_api_sets_default_when_empty(tmp_path: Path) -> None:
    conf: dict = {}
    register_api(conf, "petstore", "petstore.json", "petstore.json", "http://localhost")
    assert conf["default"] == "petstore"
    assert conf["petstore"]["url"] == "http://localhost"


def test_register_api_does_not_overwrite_default(tmp_path: Path) -> None:
    conf: dict = {"default": "existing"}
    register_api(conf, "new", "new.json", "new.json", "http://new")
    assert conf["default"] == "existing"


def test_register_api_overwrites_existing_entry() -> None:
    conf: dict = {"default": "api", "api": {"url": "http://old"}}
    register_api(conf, "api", "api.json", "api.json", "http://new")
    assert conf["api"]["url"] == "http://new"


def test_set_and_get_default_api() -> None:
    conf: dict = {}
    set_default_api(conf, "myapi")
    assert get_default_api(conf) == "myapi"


def test_get_default_api_none_when_missing() -> None:
    assert get_default_api({}) is None


# ---------------------------------------------------------------------------
# remove_api
# ---------------------------------------------------------------------------


def test_remove_api_removes_entry() -> None:
    conf: dict = {"default": "myapi", "myapi": {"url": "http://a"}}
    remove_api(conf, "myapi")
    assert "myapi" not in conf


def test_remove_api_clears_default_when_only_api() -> None:
    conf: dict = {"default": "myapi", "myapi": {"url": "http://a"}}
    remove_api(conf, "myapi")
    assert "default" not in conf


def test_remove_api_reassigns_default_to_remaining() -> None:
    conf: dict = {
        "default": "api1",
        "api1": {"url": "http://a"},
        "api2": {"url": "http://b"},
    }
    remove_api(conf, "api1")
    assert "api1" not in conf
    assert conf.get("default") == "api2"


def test_remove_api_non_default_leaves_default_unchanged() -> None:
    conf: dict = {
        "default": "api1",
        "api1": {"url": "http://a"},
        "api2": {"url": "http://b"},
    }
    remove_api(conf, "api2")
    assert "api2" not in conf
    assert conf.get("default") == "api1"


def test_remove_api_no_default_key_leaves_conf_stable() -> None:
    conf: dict = {"myapi": {"url": "http://a"}}
    remove_api(conf, "myapi")
    assert conf == {}


# ---------------------------------------------------------------------------
# logfile
# ---------------------------------------------------------------------------


def test_get_logfile_not_set() -> None:
    assert get_logfile({}) is None


def test_get_logfile_empty_string() -> None:
    assert get_logfile({"logfile": ""}) is None


def test_get_logfile_returns_path() -> None:
    assert get_logfile({"logfile": "/tmp/papycli.log"}) == "/tmp/papycli.log"


def test_set_logfile() -> None:
    conf: dict = {}
    set_logfile(conf, "/var/log/papycli.log")
    assert conf["logfile"] == "/var/log/papycli.log"


def test_unset_logfile() -> None:
    conf: dict = {"logfile": "/tmp/papycli.log"}
    unset_logfile(conf)
    assert "logfile" not in conf


def test_unset_logfile_noop_when_not_set() -> None:
    conf: dict = {}
    unset_logfile(conf)
    assert conf == {}
