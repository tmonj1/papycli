"""spec_loader モジュールのテスト."""

import json
from pathlib import Path
from typing import Any

import pytest

from papycli.spec_loader import (
    extract_base_url,
    load_spec,
    resolve_refs,
    spec_to_apidef,
)

# ---------------------------------------------------------------------------
# テスト用最小 spec
# ---------------------------------------------------------------------------

MINIMAL_SPEC: dict[str, Any] = {
    "openapi": "3.0.2",
    "servers": [{"url": "http://localhost:8080/api/v1"}],
    "paths": {
        "/items": {
            "get": {
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string", "enum": ["active", "inactive"]},
                    }
                ]
            },
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "count": {"type": "integer"},
                                },
                            }
                        }
                    }
                }
            },
        },
        "/items/{itemId}": {
            "get": {},
            "delete": {},
        },
    },
}

PETSTORE_PATH = Path(__file__).parent.parent / "examples" / "petstore" / "petstore-oas3.json"


# ---------------------------------------------------------------------------
# load_spec
# ---------------------------------------------------------------------------


def test_load_spec_json(tmp_path: Path) -> None:
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(MINIMAL_SPEC), encoding="utf-8")
    loaded = load_spec(spec_file)
    assert loaded["openapi"] == "3.0.2"


def test_load_spec_yaml(tmp_path: Path) -> None:
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("openapi: '3.0.2'\ninfo:\n  title: Test\n", encoding="utf-8")
    loaded = load_spec(spec_file)
    assert loaded["openapi"] == "3.0.2"


def test_load_spec_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_spec(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# resolve_refs
# ---------------------------------------------------------------------------


def test_resolve_refs_no_refs() -> None:
    obj = {"a": 1, "b": [2, 3]}
    assert resolve_refs(obj, obj) == obj


def test_resolve_refs_internal() -> None:
    root: dict[str, Any] = {
        "components": {"schemas": {"Item": {"type": "object", "properties": {"id": {"type": "integer"}}}}},
        "target": {"$ref": "#/components/schemas/Item"},
    }
    resolved = resolve_refs(root["target"], root)
    assert resolved == {"type": "object", "properties": {"id": {"type": "integer"}}}


def test_resolve_refs_nested() -> None:
    root: dict[str, Any] = {
        "components": {
            "schemas": {
                "A": {"$ref": "#/components/schemas/B"},
                "B": {"type": "string"},
            }
        },
        "target": {"$ref": "#/components/schemas/A"},
    }
    resolved = resolve_refs(root["target"], root)
    assert resolved == {"type": "string"}


def test_resolve_refs_circular_guard() -> None:
    """循環参照は空 dict で打ち切る（無限ループしない）。"""
    root: dict[str, Any] = {
        "components": {
            "schemas": {
                "A": {"$ref": "#/components/schemas/A"},
            }
        },
        "target": {"$ref": "#/components/schemas/A"},
    }
    result = resolve_refs(root["target"], root)
    assert result == {}


def test_resolve_refs_unsupported_ref() -> None:
    root: dict[str, Any] = {"target": {"$ref": "external.json#/foo"}}
    with pytest.raises(ValueError, match="Unsupported"):
        resolve_refs(root["target"], root)


# ---------------------------------------------------------------------------
# spec_to_apidef
# ---------------------------------------------------------------------------


def test_spec_to_apidef_paths_exist() -> None:
    apidef = spec_to_apidef(MINIMAL_SPEC)
    assert "/items" in apidef
    assert "/items/{itemId}" in apidef


def test_spec_to_apidef_query_parameter() -> None:
    apidef = spec_to_apidef(MINIMAL_SPEC)
    get_op = next(op for op in apidef["/items"] if op["method"] == "get")
    assert len(get_op["query_parameters"]) == 1
    param = get_op["query_parameters"][0]
    assert param["name"] == "status"
    assert param["type"] == "string"
    assert param["required"] is False
    assert param["enum"] == ["active", "inactive"]


def test_spec_to_apidef_post_parameters() -> None:
    apidef = spec_to_apidef(MINIMAL_SPEC)
    post_op = next(op for op in apidef["/items"] if op["method"] == "post")
    params = {p["name"]: p for p in post_op["post_parameters"]}
    assert params["name"]["required"] is True
    assert params["count"]["required"] is False
    assert params["count"]["type"] == "integer"


def test_spec_to_apidef_no_body_no_params() -> None:
    apidef = spec_to_apidef(MINIMAL_SPEC)
    get_op = next(op for op in apidef["/items/{itemId}"] if op["method"] == "get")
    assert get_op["query_parameters"] == []
    assert get_op["post_parameters"] == []


def test_spec_to_apidef_methods_only_defined() -> None:
    """定義されていないメソッドはリストに含まない。"""
    apidef = spec_to_apidef(MINIMAL_SPEC)
    methods = {op["method"] for op in apidef["/items/{itemId}"]}
    assert methods == {"get", "delete"}


# ---------------------------------------------------------------------------
# allOf
# ---------------------------------------------------------------------------


def test_spec_to_apidef_allof() -> None:
    spec: dict[str, Any] = {
        "paths": {
            "/things": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {
                                            "required": ["id"],
                                            "properties": {"id": {"type": "integer"}},
                                        },
                                        {
                                            "required": ["name"],
                                            "properties": {"name": {"type": "string"}},
                                        },
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    apidef = spec_to_apidef(spec)
    params = {p["name"]: p for p in apidef["/things"][0]["post_parameters"]}
    assert params["id"]["required"] is True
    assert params["name"]["required"] is True


# ---------------------------------------------------------------------------
# extract_base_url
# ---------------------------------------------------------------------------


def test_extract_base_url() -> None:
    spec: dict[str, Any] = {"servers": [{"url": "http://localhost:8080/api/v3"}]}
    assert extract_base_url(spec) == "http://localhost:8080/api/v3"


def test_extract_base_url_missing() -> None:
    assert extract_base_url({}) == ""


# ---------------------------------------------------------------------------
# petstore-oas3.json の統合テスト
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_spec_loads() -> None:
    spec = load_spec(PETSTORE_PATH)
    assert spec["openapi"].startswith("3.")


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_resolve_refs() -> None:
    spec = load_spec(PETSTORE_PATH)
    resolved = resolve_refs(spec, spec)
    # $ref が残っていないことを確認
    assert "$ref" not in json.dumps(resolved)


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_apidef_has_key_endpoints() -> None:
    spec = load_spec(PETSTORE_PATH)
    resolved = resolve_refs(spec, spec)
    apidef = spec_to_apidef(resolved)
    assert "/pet" in apidef
    assert "/pet/findByStatus" in apidef
    assert "/pet/{petId}" in apidef
    assert "/store/inventory" in apidef


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_find_by_status_query_param() -> None:
    spec = load_spec(PETSTORE_PATH)
    resolved = resolve_refs(spec, spec)
    apidef = spec_to_apidef(resolved)
    get_op = next(op for op in apidef["/pet/findByStatus"] if op["method"] == "get")
    param = next(p for p in get_op["query_parameters"] if p["name"] == "status")
    assert "enum" in param
    assert "available" in param["enum"]


@pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
def test_petstore_base_url() -> None:
    spec = load_spec(PETSTORE_PATH)
    assert extract_base_url(spec) == "http://localhost:8080/api/v3"
