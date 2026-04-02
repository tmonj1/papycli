"""CLI エントリポイントのテスト."""

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import responses as rsps
from click.testing import CliRunner

from papycli import __version__
from papycli.config import load_conf, save_conf
from papycli.init_cmd import init_api, register_initialized_api
from papycli.main import _load_env_files, cli

PETSTORE_PATH = Path(__file__).parent.parent.parent / "examples" / "petstore" / "petstore-oas3.json"
BASE_URL = "http://localhost:8080/api/v3"

MINIMAL_SPEC: dict[str, Any] = {
    "openapi": "3.0.2",
    "servers": [{"url": "http://localhost:9000/api"}],
    "paths": {
        "/items": {
            "get": {
                "parameters": [
                    {"name": "q", "in": "query", "required": False, "schema": {"type": "string"}}
                ]
            }
        }
    },
}


@pytest.fixture()
def minimal_spec_file(tmp_path: Path) -> Path:
    path = tmp_path / "myapi.json"
    path.write_text(json.dumps(MINIMAL_SPEC), encoding="utf-8")
    return path


@pytest.fixture()
def petstore_conf_dir(tmp_path: Path) -> Path:
    """petstore-oas3.json を add した conf dir を返す。"""
    api_name, base_url = init_api(PETSTORE_PATH, tmp_path)
    conf = load_conf(tmp_path)
    register_initialized_api(conf, api_name, PETSTORE_PATH, base_url)
    save_conf(conf, tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# 基本動作
# ---------------------------------------------------------------------------


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "papycli" in result.output


def test_no_args_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_help_shows_method_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert "get" in result.output
    assert "post" in result.output
    assert "delete" in result.output
    assert "config" in result.output


def test_config_no_subcommand_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "use" in result.output
    assert "list" in result.output


# ---------------------------------------------------------------------------
# papycli config add
# ---------------------------------------------------------------------------


def test_cmd_add_success(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    assert result.exit_code == 0
    assert "Registered API 'myapi'" in result.output
    assert "http://localhost:9000/api" in result.output


def test_cmd_add_creates_conf(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["default"] == "myapi"
    assert conf["myapi"]["url"] == "http://localhost:9000/api"


def test_cmd_add_creates_apidef(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    apidef_path = tmp_path / "apis" / "myapi.json"
    assert apidef_path.exists()


def test_cmd_add_nonexistent_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", str(tmp_path / "no_such.json")])
    assert result.exit_code != 0


def test_cmd_add_reserved_name_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A spec file named 'default.json' must be rejected before writing config."""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    spec = tmp_path / "default.json"
    spec.write_text(json.dumps(MINIMAL_SPEC), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", str(spec)])
    assert result.exit_code != 0
    assert "default" in result.output
    assert not (tmp_path / "papycli.conf").exists()


def test_cmd_add_reserved_name_logfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A spec file named 'logfile.json' must be rejected to avoid overwriting the logfile setting.
    """
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    spec = tmp_path / "logfile.json"
    spec.write_text(json.dumps(MINIMAL_SPEC), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", str(spec)])
    assert result.exit_code != 0
    assert "logfile" in result.output
    assert not (tmp_path / "papycli.conf").exists()


def test_cmd_add_already_registered_errors(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """config add を同じ API 名で2回実行するとエラーになる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    first = runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    assert first.exit_code == 0, f"1回目の add が失敗した: {first.output}"
    conf_before = (tmp_path / "papycli.conf").read_text(encoding="utf-8")
    apidef_before = (tmp_path / "apis" / "myapi.json").read_text(encoding="utf-8")

    result = runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    assert result.exit_code != 0
    assert "already registered" in result.output
    assert "--upgrade" in result.output
    assert (tmp_path / "papycli.conf").read_text(encoding="utf-8") == conf_before
    assert (tmp_path / "apis" / "myapi.json").read_text(encoding="utf-8") == apidef_before


def test_cmd_add_upgrade_updates_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--upgrade で既存 API の spec・apidef・URL が更新される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()

    # 旧 spec で登録
    old_spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://old.example.com/api"}],
        "paths": {
            "/items": {"get": {"parameters": []}},
        },
    }
    spec_file = tmp_path / "myapi.json"
    spec_file.write_text(json.dumps(old_spec), encoding="utf-8")
    first = runner.invoke(cli, ["config", "add", str(spec_file)])
    assert first.exit_code == 0, f"1回目の add が失敗した: {first.output}"

    # 新 spec で --upgrade
    new_spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://new.example.com/api"}],
        "paths": {
            "/items": {"get": {"parameters": []}},
            "/users": {"get": {"parameters": []}},
        },
    }
    spec_file.write_text(json.dumps(new_spec), encoding="utf-8")
    result = runner.invoke(cli, ["config", "add", "--upgrade", str(spec_file)])

    assert result.exit_code == 0
    assert "Updated API 'myapi'" in result.output
    assert "http://new.example.com/api" in result.output

    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["myapi"]["url"] == "http://new.example.com/api"

    apidef = json.loads((tmp_path / "apis" / "myapi.json").read_text(encoding="utf-8"))
    assert "/users" in apidef

    raw_spec = json.loads((tmp_path / "apis" / "myapi.spec.json").read_text(encoding="utf-8"))
    assert raw_spec["servers"][0]["url"] == "http://new.example.com/api"


def test_cmd_add_upgrade_on_new_api_registers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--upgrade で未登録 API を指定すると新規登録として扱われる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://localhost:9000/api"}],
        "paths": {"/items": {"get": {"parameters": []}}},
    }
    spec_file = tmp_path / "myapi.json"
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", "--upgrade", str(spec_file)])

    assert result.exit_code == 0
    assert "Registered API 'myapi'" in result.output
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["default"] == "myapi"


def test_cmd_add_upgrade_rollback_on_save_conf_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--upgrade で save_conf() が失敗した場合、apidef/spec が旧内容に復元される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()

    old_spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://old.example.com/api"}],
        "paths": {"/items": {"get": {"parameters": []}}},
    }
    spec_file = tmp_path / "myapi.json"
    spec_file.write_text(json.dumps(old_spec), encoding="utf-8")
    first = runner.invoke(cli, ["config", "add", str(spec_file)])
    assert first.exit_code == 0, f"1回目の add が失敗した: {first.output}"

    old_apidef = (tmp_path / "apis" / "myapi.json").read_bytes()
    old_raw_spec = (tmp_path / "apis" / "myapi.spec.json").read_bytes()

    new_spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://new.example.com/api"}],
        "paths": {"/items": {"get": {"parameters": []}}, "/users": {"get": {"parameters": []}}},
    }
    spec_file.write_text(json.dumps(new_spec), encoding="utf-8")

    from unittest.mock import patch
    with patch("papycli.main.save_conf", side_effect=OSError("disk full")):
        result = runner.invoke(cli, ["config", "add", "--upgrade", str(spec_file)])

    assert result.exit_code != 0
    assert (tmp_path / "apis" / "myapi.json").read_bytes() == old_apidef
    assert (tmp_path / "apis" / "myapi.spec.json").read_bytes() == old_raw_spec


# ---------------------------------------------------------------------------
# papycli config use
# ---------------------------------------------------------------------------


def test_cmd_use_switches_default(tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    spec2 = tmp_path / "otherapi.json"
    spec2.write_text(json.dumps({**MINIMAL_SPEC, "servers": [{"url": "http://other"}]}), encoding="utf-8")
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "add", str(spec2)])

    result = runner.invoke(cli, ["config", "use", "myapi"])
    assert result.exit_code == 0
    assert "myapi" in result.output

    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["default"] == "myapi"


def test_cmd_use_unknown_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "use", "unknown"])
    assert result.exit_code != 0


def test_cmd_use_reserved_key_default(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """'default' is a reserved conf key and must be rejected with a clear error."""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["config", "use", "default"])
    assert result.exit_code != 0
    assert "default" in result.output


# ---------------------------------------------------------------------------
# papycli config remove
# ---------------------------------------------------------------------------


def test_cmd_remove_success(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["config", "remove", "myapi"])
    assert result.exit_code == 0
    assert "Removed API 'myapi'" in result.output


def test_cmd_remove_deletes_conf_entry(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "remove", "myapi"])
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert "myapi" not in conf


def test_cmd_remove_deletes_apidef_file(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    apidef_path = tmp_path / "apis" / "myapi.json"
    assert apidef_path.exists()
    runner.invoke(cli, ["config", "remove", "myapi"])
    assert not apidef_path.exists()


def test_cmd_remove_deletes_raw_spec_file(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    spec_path = tmp_path / "apis" / "myapi.spec.json"
    assert spec_path.exists()
    runner.invoke(cli, ["config", "remove", "myapi"])
    assert not spec_path.exists()


def test_cmd_remove_clears_default_when_only_api(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "remove", "myapi"])
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert "default" not in conf


def test_cmd_remove_reassigns_default_when_other_apis_remain(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    spec2 = tmp_path / "otherapi.json"
    spec2_data = {**MINIMAL_SPEC, "servers": [{"url": "http://other"}]}
    spec2.write_text(json.dumps(spec2_data), encoding="utf-8")
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "add", str(spec2)])
    runner.invoke(cli, ["config", "use", "myapi"])

    result = runner.invoke(cli, ["config", "remove", "myapi"])
    assert result.exit_code == 0
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert "myapi" not in conf
    assert conf.get("default") == "otherapi"


def test_cmd_remove_unknown_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "remove", "unknown"])
    assert result.exit_code != 0


def test_cmd_remove_reserved_key_default(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["config", "remove", "default"])
    assert result.exit_code != 0
    assert "default" in result.output


# ---------------------------------------------------------------------------
# papycli config list
# ---------------------------------------------------------------------------


def test_cmd_list_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert str(tmp_path) in result.output


def test_cmd_list_after_add(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert "myapi" in result.output
    assert "http://localhost:9000/api" in result.output


# ---------------------------------------------------------------------------
# papycli get / post / delete（HTTP モック）
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_inventory(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"dogs": 2}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/store/inventory"])
    assert result.exit_code == 0
    assert "HTTP 200" not in result.output
    assert "dogs" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_inventory_verbose(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"dogs": 2}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/store/inventory", "--verbose"])
    assert result.exit_code == 0
    assert "HTTP 200" in result.output
    assert "dogs" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_with_path_param(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/pet/99", json={"id": 99, "name": "Rex"}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/99"])
    assert result.exit_code == 0
    assert "99" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_with_query_param(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/pet/findByStatus", json=[], status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/findByStatus", "-q", "status", "available"])
    assert result.exit_code == 0
    req = rsps.calls[0].request
    assert "status=available" in req.url


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_post_with_body_params(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "post", "/pet",
        "-p", "name", "My Dog",
        "-p", "status", "available",
        "-p", "photoUrls", "http://example.com/a.jpg",
    ])
    assert result.exit_code == 0
    body = json.loads(rsps.calls[0].request.body)
    assert body["name"] == "My Dog"
    assert body["status"] == "available"


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_post_with_raw_body(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    raw = json.dumps({"name": "Dog", "status": "available", "photoUrls": []})
    runner = CliRunner()
    result = runner.invoke(cli, ["post", "/pet", "-d", raw])
    assert result.exit_code == 0


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_delete(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.DELETE, f"{BASE_URL}/pet/1", status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "/pet/1"])
    assert result.exit_code == 0


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_delete_204_shows_status_on_stderr(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """204 No Content (空ボディ) はステータス行を stderr に出す。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.DELETE, f"{BASE_URL}/pet/1", status=204, body=b"")

    echo_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        echo_calls.append((args, kwargs))

    runner = CliRunner()
    with patch("papycli.main.click.echo", side_effect=capture):
        result = runner.invoke(cli, ["delete", "/pet/1"])
    assert result.exit_code == 0
    assert any("HTTP 204" in str(a[0]) and kw.get("err") is True for a, kw in echo_calls)


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_error_shows_status_on_stderr(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """非 2xx レスポンスはステータス行を stderr に出す。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"message": "not found"}, status=404)

    echo_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        echo_calls.append((args, kwargs))

    runner = CliRunner()
    with patch("papycli.main.click.echo", side_effect=capture):
        result = runner.invoke(cli, ["get", "/store/inventory"])
    assert result.exit_code == 0
    assert any("HTTP 404" in str(a[0]) and kw.get("err") is True for a, kw in echo_calls)


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_with_inline_query_string(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """リソースパスのインラインクエリ文字列が -q と同様に送信される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/pet/findByStatus", json=[], status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/findByStatus?status=available"])
    assert result.exit_code == 0
    req = rsps.calls[0].request
    assert "status=available" in req.url


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_with_inline_query_multiple_params(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """インラインクエリ文字列の複数パラメータが全て送信される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/pet/findByStatus", json=[], status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/findByStatus?status=available&limit=10"])
    assert result.exit_code == 0
    req = rsps.calls[0].request
    assert "status=available" in req.url
    assert "limit=10" in req.url


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_inline_query_and_explicit_q_combined(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """インラインクエリ文字列と -q オプションを併用すると両方が送信される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.GET, f"{BASE_URL}/pet/findByStatus", json=[], status=200)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["get", "/pet/findByStatus?status=available", "-q", "limit", "5"]
    )
    assert result.exit_code == 0
    req = rsps.calls[0].request
    assert "status=available" in req.url
    assert "limit=5" in req.url
    # インラインクエリパラメータは -q パラメータより前に送信される
    assert req.url.index("status=available") < req.url.index("limit=5")


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_get_unknown_path(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/nonexistent/path"])
    assert result.exit_code != 0


def test_cmd_get_no_conf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/anything"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# papycli --check オプション
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_check_warns_missing_required(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """必須パラメータ不足時に警告を出力し、リクエストは送信する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["post", "/pet", "--check"])
    assert result.exit_code == 0
    assert len(rsps.calls) == 1  # リクエストは送信された
    assert "missing" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_check_warns_enum_violation(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "post", "/pet", "--check",
        "-p", "name", "Rex",
        "-p", "photoUrls", "http://example.com/a.jpg",
        "-p", "status", "invalid_status",
    ])
    assert result.exit_code == 0
    assert len(rsps.calls) == 1
    assert "enum" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_check_no_warning_when_valid(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "post", "/pet", "--check",
        "-p", "name", "Rex",
        "-p", "photoUrls", "http://example.com/a.jpg",
        "-p", "status", "available",
    ])
    assert result.exit_code == 0
    assert len(rsps.calls) == 1
    assert "Warning" not in result.output


# ---------------------------------------------------------------------------
# papycli <method> --check-strict
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_check_strict_aborts_on_failure(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """必須パラメータ不足時に警告を出力し、リクエストを中止して exit 1 する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, ["post", "/pet", "--check-strict"])
    assert result.exit_code == 1
    assert len(rsps.calls) == 0  # リクエストは送信されない
    assert "missing" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_check_strict_sends_when_valid(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """チェック問題なし時はリクエストを送信する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "post", "/pet", "--check-strict",
        "-p", "name", "Rex",
        "-p", "photoUrls", "http://example.com/a.jpg",
        "-p", "status", "available",
    ])
    assert result.exit_code == 0
    assert len(rsps.calls) == 1
    assert "Warning" not in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_check_and_check_strict_mutually_exclusive(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--check と --check-strict の同時指定はエラーになる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["post", "/pet", "--check", "--check-strict"])
    assert result.exit_code == 1
    assert "cannot be used together" in result.output


# ---------------------------------------------------------------------------
# papycli summary
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_summary_all(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["summary"])
    assert result.exit_code == 0
    assert "/pet" in result.output
    assert "/store/inventory" in result.output
    assert "GET" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_summary_filtered(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", "/pet"])
    assert result.exit_code == 0
    assert "/pet" in result.output
    assert "/store" not in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_summary_csv(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", "--csv"])
    assert result.exit_code == 0
    assert result.output.startswith("method,path,")
    assert "GET" in result.output
    assert "/pet/findByStatus" in result.output


def test_cmd_summary_no_conf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["summary"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# papycli spec
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_all(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "/pet" in data
    assert "/store/inventory" in data


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_resource_exact(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "/pet/findByStatus"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "/pet/findByStatus" in data
    assert "/pet" not in data
    assert "/store/inventory" not in data


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_resource_via_template(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "/pet/99"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "/pet/{petId}" in data


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_resource_not_found(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "/no/such/path"])
    assert result.exit_code != 0


def test_cmd_spec_no_conf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec"])
    assert result.exit_code != 0


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_full(petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "openapi" in data
    assert "paths" in data


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_full_contains_raw_paths(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # 内部 apidef 形式ではなく OpenAPI spec 形式であることを確認（get/post などのキーを持つ）
    paths = data["paths"]
    pet_ops = paths.get("/pet", {})
    assert any(method in pet_ops for method in ("get", "post", "put", "patch", "delete"))


def test_cmd_spec_full_no_conf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full"])
    assert result.exit_code != 0


def test_cmd_spec_full_minimal(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["spec", "--full"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["openapi"] == "3.0.2"
    assert "/items" in data["paths"]


def test_cmd_spec_full_with_resource_minimal(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["spec", "--full", "/items"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "/items" in data
    # raw spec 形式（HTTP メソッドがキー）
    assert "get" in data["/items"]


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_full_with_resource_exact(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full", "/pet/findByStatus"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "/pet/findByStatus" in data
    assert "/pet" not in data
    assert "get" in data["/pet/findByStatus"]


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_full_with_resource_via_template(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full", "/pet/99"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "/pet/{petId}" in data


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_full_with_resource_not_found(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full", "/no/such/path"])
    assert result.exit_code != 0


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_spec_full_with_resource_includes_schemas(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/pet の --full 出力に参照スキーマ (Pet) が components.schemas に含まれる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["spec", "--full", "/pet"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "components" in data
    assert "schemas" in data["components"]
    assert "Pet" in data["components"]["schemas"]


def test_cmd_spec_full_with_resource_no_refs_no_components(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """$ref のない仕様では components キーが出力されない。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["spec", "--full", "/items"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "components" not in data


# ---------------------------------------------------------------------------
# papycli get --summary (エンドポイント詳細表示)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_get_with_summary_flag(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/findByStatus", "--summary"])
    assert result.exit_code == 0
    assert "GET" in result.output
    assert "/pet/findByStatus" in result.output
    assert "status" in result.output
    # HTTP リクエストは送らない（responses モックなしで成功する）


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_get_with_summary_flag_path_param(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/99", "--summary"])
    assert result.exit_code == 0
    assert "/pet/{petId}" in result.output


# ---------------------------------------------------------------------------
# papycli get --response-check
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_response_check_valid(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """スキーマに適合したレスポンスは警告なし。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(
        rsps.GET, f"{BASE_URL}/pet/1",
        json={"id": 1, "name": "Rex", "photoUrls": []},
        status=200,
        content_type="application/json",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/1", "--response-check"])
    combined = result.output + getattr(result, "stderr", "")
    assert result.exit_code == 0
    assert "[response]" not in combined


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_response_check_violation(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """型違反があると出力に [response] 警告が含まれる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    # id が string（本来は integer）
    rsps.add(
        rsps.GET, f"{BASE_URL}/pet/1",
        json={"id": "not_an_int", "name": "Rex", "photoUrls": []},
        status=200,
        content_type="application/json",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/1", "--response-check"])
    combined = result.output + getattr(result, "stderr", "")
    assert result.exit_code == 0
    assert "[response]" in combined


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
@rsps.activate
def test_cmd_response_check_without_flag_no_warning(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--response-check なしは型違反があっても警告しない。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    rsps.add(
        rsps.GET, f"{BASE_URL}/pet/1",
        json={"id": "not_an_int"},
        status=200,
        content_type="application/json",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/pet/1"])
    combined = result.output + getattr(result, "stderr", "")
    assert result.exit_code == 0
    assert "[response]" not in combined


# ---------------------------------------------------------------------------
# papycli config completion-script
# ---------------------------------------------------------------------------


def test_cmd_completion_script_bash() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "completion-script", "bash"], prog_name="papycli")
    assert result.exit_code == 0
    assert "_papycli_completion" in result.output
    assert "_complete" not in result.output


def test_cmd_completion_script_zsh() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "completion-script", "zsh"], prog_name="papycli")
    assert result.exit_code == 0
    assert "compdef" in result.output
    assert "_complete" not in result.output


def test_cmd_completion_script_invalid_shell() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "completion-script", "fish"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# papycli _complete (内部補完コマンド)
# ---------------------------------------------------------------------------


def test_cmd_complete_subcommands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["_complete", "1", "papycli", ""])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "post" in result.output
    assert "config" in result.output
    assert "init" not in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_complete_resources(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(cli, ["_complete", "2", "papycli", "get", ""])
    assert result.exit_code == 0
    assert "/pet" in result.output
    assert "/store/inventory" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_complete_query_param_names(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(
        cli, ["_complete", "4", "papycli", "get", "/pet/findByStatus", "-q", ""]
    )
    assert result.exit_code == 0
    assert "status" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_complete_enum_values(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["_complete", "5", "papycli", "get", "/pet/findByStatus", "-q", "status", ""],
    )
    assert result.exit_code == 0
    assert "available" in result.output
    assert "pending" in result.output
    assert "sold" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_complete_body_param_names(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(
        cli, ["_complete", "4", "papycli", "post", "/pet", "-p", ""]
    )
    assert result.exit_code == 0
    assert "name" in result.output
    assert "status" in result.output
    assert "photoUrls" in result.output


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_cmd_complete_body_enum_values(
    petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
    runner = CliRunner()
    result = runner.invoke(
        cli, ["_complete", "5", "papycli", "post", "/pet", "-p", "status", ""]
    )
    assert result.exit_code == 0
    assert "available" in result.output
    assert "pending" in result.output
    assert "sold" in result.output


def test_cmd_complete_output_no_crlf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`_complete` の出力が LF のみで、CR を含まないことを確認する (Windows 対応)。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["_complete", "1", "papycli", ""])
    assert result.exit_code == 0
    assert "\r" not in result.output
    assert "get" in result.output


# ---------------------------------------------------------------------------
# config log
# ---------------------------------------------------------------------------


def test_config_log_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """logfile が未設定のとき '(not set)' を表示する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "log"])
    assert result.exit_code == 0
    assert "(not set)" in result.output


def test_config_log_set_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PATH を指定すると papycli.conf の logfile が更新され確認メッセージが出る。"""
    import json as _json
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    logpath = str(tmp_path / "papycli.log")
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "log", logpath])
    assert result.exit_code == 0
    assert logpath in result.output

    conf_path = tmp_path / "papycli.conf"
    conf = _json.loads(conf_path.read_text(encoding="utf-8"))
    assert conf["logfile"] == logpath


def test_config_log_show_after_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """logfile 設定後に引数なしで呼ぶとパスが表示される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    logpath = "/tmp/papycli.log"
    runner = CliRunner()
    runner.invoke(cli, ["config", "log", logpath])
    result = runner.invoke(cli, ["config", "log"])
    assert result.exit_code == 0
    assert logpath in result.output


def test_config_log_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--unset で logfile 設定が削除される。"""
    import json as _json
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "log", "/tmp/papycli.log"])
    result = runner.invoke(cli, ["config", "log", "--unset"])
    assert result.exit_code == 0
    assert "removed" in result.output

    conf_path = tmp_path / "papycli.conf"
    conf = _json.loads(conf_path.read_text(encoding="utf-8"))
    assert "logfile" not in conf


def test_config_log_unset_and_path_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--unset と PATH を同時指定するとエラー終了する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "log", "--unset", "/some/path"])
    assert result.exit_code != 0
    assert "Error" in result.output or "Error" in (result.stderr if hasattr(result, "stderr") else "")


# ---------------------------------------------------------------------------
# config alias
# ---------------------------------------------------------------------------


@pytest.fixture()
def alias_conf_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """petstore-oas3.json を登録した conf_dir を返す（alias テスト用）。"""
    if not PETSTORE_PATH.exists():
        pytest.skip("petstore-oas3.json not found")
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", str(PETSTORE_PATH)])
    assert result.exit_code == 0, f"config add failed: {result.output}"
    return tmp_path


@pytest.fixture(scope="session")
def symlinks_supported(tmp_path_factory: pytest.TempPathFactory) -> bool:
    """セッションスコープで symlink が使えるか確認する。"""
    p = tmp_path_factory.mktemp("symlink_check")
    try:
        (p / "link").symlink_to(p / "target")
        (p / "link").unlink()
        return True
    except (OSError, NotImplementedError):
        return False


def test_config_alias_list_empty(alias_conf_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias"])
    assert result.exit_code == 0
    assert "no aliases" in result.output


def test_config_alias_create(
    alias_conf_dir: Path, symlinks_supported: bool,
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    if not symlinks_supported:
        pytest.skip("symlinks not supported on this platform")
    import json as _json
    import papycli.main as _main

    fake_exe = tmp_path / "papycli"
    fake_exe.touch()
    monkeypatch.setattr(_main.shutil, "which", lambda name: str(fake_exe))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias", "petcli", "petstore-oas3"])
    assert result.exit_code == 0, result.output
    assert "petcli" in result.output

    conf = _json.loads((alias_conf_dir / "papycli.conf").read_text(encoding="utf-8"))
    assert conf.get("aliases", {}).get("petcli") == "petstore-oas3"
    symlink = alias_conf_dir / "bin" / "petcli"
    assert symlink.is_symlink()
    assert symlink.resolve() == fake_exe.resolve()


def test_config_alias_create_defaults_to_default_spec(
    alias_conf_dir: Path, symlinks_supported: bool,
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    if not symlinks_supported:
        pytest.skip("symlinks not supported on this platform")
    import json as _json
    import papycli.main as _main

    fake_exe = tmp_path / "papycli"
    fake_exe.touch()
    monkeypatch.setattr(_main.shutil, "which", lambda name: str(fake_exe))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias", "petcli"])
    assert result.exit_code == 0, result.output

    conf = _json.loads((alias_conf_dir / "papycli.conf").read_text(encoding="utf-8"))
    default_spec = conf.get("default")
    assert conf.get("aliases", {}).get("petcli") == default_spec
    symlink = alias_conf_dir / "bin" / "petcli"
    assert symlink.is_symlink()
    assert symlink.resolve() == fake_exe.resolve()


def test_config_alias_list_shows_aliases(alias_conf_dir: Path) -> None:
    import json as _json
    # config alias コマンド（symlink 作成を伴う）を使わず conf を直接書き換えてリスト表示を検証する
    conf_path = alias_conf_dir / "papycli.conf"
    conf = _json.loads(conf_path.read_text(encoding="utf-8"))
    conf.setdefault("aliases", {})["petcli"] = "petstore-oas3"
    conf_path.write_text(_json.dumps(conf, ensure_ascii=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias"])
    assert result.exit_code == 0
    assert "petcli" in result.output
    assert "petstore-oas3" in result.output


def test_config_alias_delete(
    alias_conf_dir: Path, symlinks_supported: bool,
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    if not symlinks_supported:
        pytest.skip("symlinks not supported on this platform")
    import json as _json
    import papycli.main as _main

    fake_exe = tmp_path / "papycli"
    fake_exe.touch()
    monkeypatch.setattr(_main.shutil, "which", lambda name: str(fake_exe))

    runner = CliRunner()
    runner.invoke(cli, ["config", "alias", "petcli", "petstore-oas3"])
    result = runner.invoke(cli, ["config", "alias", "-d", "petcli"])
    assert result.exit_code == 0
    assert "removed" in result.output

    conf = _json.loads((alias_conf_dir / "papycli.conf").read_text(encoding="utf-8"))
    assert "petcli" not in conf.get("aliases", {})
    assert not (alias_conf_dir / "bin" / "petcli").exists()


def test_config_alias_delete_nonexistent(alias_conf_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias", "-d", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_config_alias_unknown_spec(alias_conf_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias", "petcli", "no-such-spec"])
    assert result.exit_code != 0
    assert "not registered" in result.output


def test_config_alias_delete_requires_name(alias_conf_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "alias", "-d"])
    assert result.exit_code != 0
    assert "alias name is required" in result.output


def test_alias_detection_sets_api_override(
    alias_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """argv[0] がエイリアス名と一致するとき、対応する spec が set_api_override で設定される。"""
    import json as _json
    import papycli.main as _main

    # config alias コマンド（symlink 作成を伴う）を使わず conf を直接書き換える
    conf_path = alias_conf_dir / "papycli.conf"
    conf = _json.loads(conf_path.read_text(encoding="utf-8"))
    conf.setdefault("aliases", {})["petcli"] = "petstore-oas3"
    conf_path.write_text(_json.dumps(conf, ensure_ascii=False), encoding="utf-8")

    overrides: list[str | None] = []
    original = _main.set_api_override

    def _capture(name: str | None) -> None:
        original(name)
        overrides.append(name)

    # main.py は `from papycli.config import set_api_override` でインポートしているため、
    # main モジュール上の名前をパッチする
    monkeypatch.setattr(_main, "set_api_override", _capture)

    runner = CliRunner()
    result = runner.invoke(cli, ["summary"], prog_name="petcli")
    assert result.exit_code == 0

    # set_api_override が "petstore-oas3" で呼ばれていること
    assert "petstore-oas3" in overrides


class TestCompletionScriptStatic:
    def test_bash_no_python_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """生成スクリプトに _complete 呼び出しが含まれないこと。"""
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "completion-script", "bash"], prog_name="papycli")
        assert result.exit_code == 0
        assert "_complete" not in result.output
        assert "_papycli_completion()" in result.output

    def test_zsh_no_python_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "completion-script", "zsh"], prog_name="papycli")
        assert result.exit_code == 0
        assert "_complete" not in result.output
        assert "compdef _papycli papycli" in result.output

    @pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
    def test_bash_with_apidef_contains_resources(
        self, petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """apidef がある場合、生成スクリプトにリソースパスが含まれること。"""
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "completion-script", "bash"])
        assert result.exit_code == 0
        assert "_complete" not in result.output
        assert "/pet" in result.output
        assert "/store/inventory" in result.output


class TestLoadEnvFiles:
    def test_loads_cwd_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """カレントディレクトリの .env が読み込まれること。"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR_CWD=hello_cwd\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_VAR_CWD", raising=False)

        _load_env_files()

        assert os.environ.get("TEST_VAR_CWD") == "hello_cwd"

    def test_loads_conf_dir_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """PAPYCLI_CONF_DIR 配下の .env が読み込まれること。"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR_CONF=hello_conf\n", encoding="utf-8")
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
        monkeypatch.delenv("TEST_VAR_CONF", raising=False)
        cwd_without_env = tmp_path / "subdir"
        cwd_without_env.mkdir()
        monkeypatch.chdir(cwd_without_env)

        _load_env_files()

        assert os.environ.get("TEST_VAR_CONF") == "hello_conf"

    def test_shell_env_takes_precedence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """シェルで既にセットされた環境変数が .env の値で上書きされないこと。"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR_OVERRIDE=from_dotenv\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TEST_VAR_OVERRIDE", "from_shell")

        _load_env_files()

        assert os.environ.get("TEST_VAR_OVERRIDE") == "from_shell"

    def test_no_error_when_no_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """.env が存在しない場合にエラーにならないこと。"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))

        _load_env_files()

    def test_cwd_takes_precedence_over_conf_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """カレントディレクトリの .env が PAPYCLI_CONF_DIR の .env より優先されること。"""
        cwd_dir = tmp_path / "cwd"
        conf_dir = tmp_path / "conf"
        cwd_dir.mkdir()
        conf_dir.mkdir()
        (cwd_dir / ".env").write_text("TEST_VAR_PRIO=from_cwd\n", encoding="utf-8")
        (conf_dir / ".env").write_text("TEST_VAR_PRIO=from_conf\n", encoding="utf-8")
        monkeypatch.chdir(cwd_dir)
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(conf_dir))
        monkeypatch.delenv("TEST_VAR_PRIO", raising=False)

        _load_env_files()

        assert os.environ.get("TEST_VAR_PRIO") == "from_cwd"
