"""init_cmd モジュールのテスト."""

import json
from pathlib import Path
from typing import Any

import pytest

from papycli.init_cmd import init_api, register_initialized_api

PETSTORE_PATH = Path(__file__).parent.parent / "examples" / "petstore-oas3.json"

MINIMAL_SPEC: dict[str, Any] = {
    "openapi": "3.0.2",
    "servers": [{"url": "http://localhost:9000/api"}],
    "paths": {
        "/items": {
            "get": {
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                    }
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


# ---------------------------------------------------------------------------
# init_api
# ---------------------------------------------------------------------------


def test_init_api_returns_name_and_url(tmp_path: Path, minimal_spec_file: Path) -> None:
    name, url = init_api(minimal_spec_file, tmp_path)
    assert name == "myapi"
    assert url == "http://localhost:9000/api"


def test_init_api_creates_apidef_file(tmp_path: Path, minimal_spec_file: Path) -> None:
    init_api(minimal_spec_file, tmp_path)
    apidef_path = tmp_path / "apis" / "myapi.json"
    assert apidef_path.exists()


def test_init_api_apidef_content(tmp_path: Path, minimal_spec_file: Path) -> None:
    init_api(minimal_spec_file, tmp_path)
    apidef = json.loads((tmp_path / "apis" / "myapi.json").read_text(encoding="utf-8"))
    assert "/items" in apidef
    get_op = next(op for op in apidef["/items"] if op["method"] == "get")
    assert get_op["query_parameters"][0]["name"] == "q"


def test_init_api_creates_apis_dir(tmp_path: Path, minimal_spec_file: Path) -> None:
    apis_dir = tmp_path / "apis"
    assert not apis_dir.exists()
    init_api(minimal_spec_file, tmp_path)
    assert apis_dir.is_dir()


def test_init_api_creates_raw_spec_file(tmp_path: Path, minimal_spec_file: Path) -> None:
    init_api(minimal_spec_file, tmp_path)
    spec_path = tmp_path / "apis" / "myapi.spec.json"
    assert spec_path.exists()


def test_init_api_raw_spec_content(tmp_path: Path, minimal_spec_file: Path) -> None:
    init_api(minimal_spec_file, tmp_path)
    raw_spec = json.loads((tmp_path / "apis" / "myapi.spec.json").read_text(encoding="utf-8"))
    assert raw_spec["openapi"] == "3.0.2"
    assert "/items" in raw_spec["paths"]


def test_init_api_no_servers_returns_empty_url(tmp_path: Path) -> None:
    spec_no_server: dict[str, Any] = {"openapi": "3.0.2", "paths": {}}
    spec_file = tmp_path / "noserver.json"
    spec_file.write_text(json.dumps(spec_no_server), encoding="utf-8")
    _, url = init_api(spec_file, tmp_path)
    assert url == ""


# ---------------------------------------------------------------------------
# register_initialized_api
# ---------------------------------------------------------------------------


def test_register_initialized_api(tmp_path: Path, minimal_spec_file: Path) -> None:
    conf: dict[str, Any] = {}
    register_initialized_api(conf, "myapi", minimal_spec_file, "http://localhost:9000/api")
    assert conf["myapi"]["openapispec"] == "myapi.json"
    assert conf["myapi"]["apidef"] == "myapi.json"
    assert conf["myapi"]["url"] == "http://localhost:9000/api"
    assert conf["default"] == "myapi"


def test_register_initialized_api_does_not_change_existing_default(
    tmp_path: Path, minimal_spec_file: Path
) -> None:
    conf: dict[str, Any] = {"default": "other"}
    register_initialized_api(conf, "myapi", minimal_spec_file, "http://localhost")
    assert conf["default"] == "other"


# ---------------------------------------------------------------------------
# petstore 統合テスト
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_init_api(tmp_path: Path) -> None:
    name, url = init_api(PETSTORE_PATH, tmp_path)
    assert name == "petstore-oas3"
    assert url == "http://localhost:8080/api/v3"


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_apidef_file_valid_json(tmp_path: Path) -> None:
    init_api(PETSTORE_PATH, tmp_path)
    apidef_path = tmp_path / "apis" / "petstore-oas3.json"
    apidef = json.loads(apidef_path.read_text(encoding="utf-8"))
    assert isinstance(apidef, dict)
    assert "/pet" in apidef
    assert "/store/inventory" in apidef


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_apidef_no_dollar_ref(tmp_path: Path) -> None:
    """生成した apidef ファイルに $ref が残っていないこと。"""
    init_api(PETSTORE_PATH, tmp_path)
    raw = (tmp_path / "apis" / "petstore-oas3.json").read_text(encoding="utf-8")
    assert "$ref" not in raw
