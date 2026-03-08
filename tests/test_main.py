"""CLI エントリポイントのテスト."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import responses as rsps
from click.testing import CliRunner

from papycli import __version__
from papycli.config import load_conf, save_conf
from papycli.init_cmd import init_api, register_initialized_api
from papycli.main import cli

PETSTORE_PATH = Path(__file__).parent.parent / "examples" / "petstore-oas3.json"
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
# papycli config completion-script
# ---------------------------------------------------------------------------


def test_cmd_completion_script_bash() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "completion-script", "bash"])
    assert result.exit_code == 0
    assert "_papycli_completion" in result.output
    assert "papycli _complete" in result.output


def test_cmd_completion_script_zsh() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "completion-script", "zsh"])
    assert result.exit_code == 0
    assert "compdef" in result.output
    assert "papycli _complete" in result.output


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
