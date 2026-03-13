"""response_checker モジュールのテスト."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from papycli.response_checker import check_response, _check_value, _type_matches


# ---------------------------------------------------------------------------
# _type_matches
# ---------------------------------------------------------------------------


def test_type_matches_string() -> None:
    assert _type_matches("hello", "string") is True
    assert _type_matches(1, "string") is False


def test_type_matches_integer() -> None:
    assert _type_matches(1, "integer") is True
    assert _type_matches(True, "integer") is False  # bool は integer ではない
    assert _type_matches(1.5, "integer") is False


def test_type_matches_number() -> None:
    assert _type_matches(1.5, "number") is True
    assert _type_matches(1, "number") is True
    assert _type_matches(True, "number") is False


def test_type_matches_boolean() -> None:
    assert _type_matches(True, "boolean") is True
    assert _type_matches(1, "boolean") is False


def test_type_matches_array() -> None:
    assert _type_matches([], "array") is True
    assert _type_matches({}, "array") is False


def test_type_matches_object() -> None:
    assert _type_matches({}, "object") is True
    assert _type_matches([], "object") is False


def test_type_matches_null() -> None:
    assert _type_matches(None, "null") is True
    assert _type_matches(0, "null") is False


def test_type_matches_unknown() -> None:
    assert _type_matches("anything", "custom") is True


# ---------------------------------------------------------------------------
# _check_value
# ---------------------------------------------------------------------------


def test_check_value_type_mismatch() -> None:
    warnings: list[str] = []
    _check_value(123, {"type": "string"}, "/name", warnings)
    assert len(warnings) == 1
    assert "expected string" in warnings[0]
    assert "got integer" in warnings[0]


def test_check_value_type_ok() -> None:
    warnings: list[str] = []
    _check_value("hello", {"type": "string"}, "/name", warnings)
    assert warnings == []


def test_check_value_enum_violation() -> None:
    warnings: list[str] = []
    _check_value("unknown", {"type": "string", "enum": ["a", "b"]}, "/status", warnings)
    assert any("not in enum" in w for w in warnings)


def test_check_value_enum_ok() -> None:
    warnings: list[str] = []
    _check_value("a", {"type": "string", "enum": ["a", "b"]}, "/status", warnings)
    assert warnings == []


def test_check_value_null_not_in_enum() -> None:
    """null 値が enum に含まれない場合は警告する（type が null を許可していても）。"""
    warnings: list[str] = []
    _check_value(None, {"type": ["string", "null"], "enum": ["a", "b"]}, "/x", warnings)
    assert any("not in enum" in w for w in warnings)


def test_check_value_null_in_enum_ok() -> None:
    """null 値が enum に含まれる場合は警告しない。"""
    warnings: list[str] = []
    _check_value(None, {"type": ["string", "null"], "enum": ["a", None]}, "/x", warnings)
    assert warnings == []


def test_check_value_required_missing() -> None:
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
        },
    }
    _check_value({"id": 1}, schema, "", warnings)
    assert any("required field 'name' is missing" in w for w in warnings)


def test_check_value_required_present() -> None:
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": "object",
        "required": ["id"],
        "properties": {"id": {"type": "integer"}},
    }
    _check_value({"id": 1}, schema, "", warnings)
    assert warnings == []


def test_check_value_nested_type_mismatch() -> None:
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
    }
    _check_value({"count": "oops"}, schema, "", warnings)
    assert any("expected integer" in w for w in warnings)


def test_check_value_additional_properties_false() -> None:
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
        "additionalProperties": False,
    }
    _check_value({"id": 1, "extra": "x"}, schema, "", warnings)
    assert any("unexpected field 'extra'" in w for w in warnings)


def test_check_value_additional_properties_not_false() -> None:
    """additionalProperties が false 以外の場合は余分フィールドを報告しない。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
    }
    _check_value({"id": 1, "extra": "x"}, schema, "", warnings)
    assert warnings == []


def test_check_value_array_items() -> None:
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": "array",
        "items": {"type": "integer"},
    }
    _check_value([1, "bad", 3], schema, "", warnings)
    assert any("expected integer" in w for w in warnings)
    assert any("[1]" in w for w in warnings)


def test_check_value_path_shown_in_root() -> None:
    """パスが空文字の場合は '/' として表示される。"""
    warnings: list[str] = []
    _check_value("x", {"type": "integer"}, "", warnings)
    assert "/:" in warnings[0]


def test_check_value_no_type_with_properties() -> None:
    """type が省略されていても properties があれば required チェックが行われる。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "required": ["id"],
        "properties": {"id": {"type": "integer"}},
    }
    _check_value({"name": "foo"}, schema, "", warnings)
    assert any("required field 'id' is missing" in w for w in warnings)


def test_check_value_no_type_with_properties_not_dict() -> None:
    """type が省略されているが object キーワードがある場合、dict 以外は型違反として警告する。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "properties": {"id": {"type": "integer"}},
    }
    _check_value("not_an_object", schema, "/x", warnings)
    assert any("expected object" in w for w in warnings)


def test_check_value_no_type_with_properties_null() -> None:
    """type 省略 + object キーワードありのスキーマで null は型違反として警告する。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "properties": {"id": {"type": "integer"}},
    }
    _check_value(None, schema, "/x", warnings)
    assert any("expected object" in w for w in warnings)


def test_check_value_no_type_with_items_not_list() -> None:
    """type が省略されているが items がある場合、list 以外は型違反として警告する。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {"items": {"type": "integer"}}
    _check_value("not_an_array", schema, "/x", warnings)
    assert any("expected array" in w for w in warnings)


def test_check_value_no_type_with_items_null() -> None:
    """type 省略 + items ありのスキーマで null は型違反として警告する。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {"items": {"type": "integer"}}
    _check_value(None, schema, "/x", warnings)
    assert any("expected array" in w for w in warnings)


def test_check_value_list_type_match() -> None:
    """type がリスト（union 型）の場合、いずれかの型と一致すれば OK。"""
    warnings: list[str] = []
    _check_value("hello", {"type": ["string", "null"]}, "/x", warnings)
    assert warnings == []


def test_check_value_list_type_mismatch() -> None:
    """type がリストでいずれにも一致しない場合は警告する。"""
    warnings: list[str] = []
    _check_value(123, {"type": ["string", "null"]}, "/x", warnings)
    assert any("expected one of" in w for w in warnings)


def test_check_value_no_type_with_items() -> None:
    """type が省略されていても items があれば配列アイテム検証が行われる。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {"items": {"type": "integer"}}
    _check_value([1, "bad"], schema, "", warnings)
    assert any("expected integer" in w for w in warnings)


def test_check_value_union_type_object_validates_properties() -> None:
    """type が ["object", "null"] の場合でもオブジェクト検証が行われる。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": ["object", "null"],
        "required": ["id"],
        "properties": {"id": {"type": "integer"}},
    }
    _check_value({"name": "foo"}, schema, "", warnings)
    assert any("required field 'id' is missing" in w for w in warnings)


def test_check_value_union_type_array_validates_items() -> None:
    """type が ["array", "null"] の場合でも配列アイテム検証が行われる。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {
        "type": ["array", "null"],
        "items": {"type": "integer"},
    }
    _check_value([1, "bad"], schema, "/tags", warnings)
    assert any("expected integer" in w for w in warnings)


def test_check_value_root_array_path_starts_with_slash() -> None:
    """ルートレベルの配列アイテムのパスが '/' から始まる。"""
    warnings: list[str] = []
    schema: dict[str, Any] = {"type": "array", "items": {"type": "integer"}}
    _check_value([1, "bad"], schema, "", warnings)
    assert warnings
    assert warnings[0].startswith("[response] /[")


# ---------------------------------------------------------------------------
# check_response
# ---------------------------------------------------------------------------


def _make_resp(
    body: Any,
    status_code: int = 200,
    content_type: str = "application/json",
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"Content-Type": content_type}
    resp.json.return_value = body
    return resp


SIMPLE_SPEC: dict[str, Any] = {
    "paths": {
        "/items": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["id"],
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "status": {
                                            "type": "string",
                                            "enum": ["active", "inactive"],
                                        },
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


def test_check_response_valid() -> None:
    resp = _make_resp({"id": 1, "name": "foo", "status": "active"})
    assert check_response(resp, SIMPLE_SPEC, "get", "/items") == []


def test_check_response_missing_required() -> None:
    resp = _make_resp({"name": "foo"})
    warnings = check_response(resp, SIMPLE_SPEC, "get", "/items")
    assert any("required field 'id' is missing" in w for w in warnings)


def test_check_response_type_mismatch() -> None:
    resp = _make_resp({"id": "not_an_int"})
    warnings = check_response(resp, SIMPLE_SPEC, "get", "/items")
    assert any("expected integer" in w for w in warnings)


def test_check_response_enum_violation() -> None:
    resp = _make_resp({"id": 1, "status": "unknown"})
    warnings = check_response(resp, SIMPLE_SPEC, "get", "/items")
    assert any("not in enum" in w for w in warnings)


def test_check_response_non_json_content_type() -> None:
    """Content-Type が application/json 以外のときはスキップ。"""
    resp = _make_resp("<html>", content_type="text/html")
    assert check_response(resp, SIMPLE_SPEC, "get", "/items") == []


def test_check_response_plus_json_content_type() -> None:
    """application/problem+json のような +json メディアタイプもチェック対象となる。"""
    spec: dict[str, Any] = {
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/problem+json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id"],
                                        "properties": {"id": {"type": "integer"}},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    resp = _make_resp({"name": "foo"}, content_type="application/problem+json")
    warnings = check_response(resp, spec, "get", "/items")
    assert any("required field 'id' is missing" in w for w in warnings)


def test_check_response_no_response_def() -> None:
    """スキーマ定義がないステータスコードは空リストを返す。"""
    resp = _make_resp({"error": "not found"}, status_code=404)
    assert check_response(resp, SIMPLE_SPEC, "get", "/items") == []


def test_check_response_default_fallback() -> None:
    """status が一致しない場合は 'default' 定義を使う。"""
    spec: dict[str, Any] = {
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "default": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["message"],
                                        "properties": {
                                            "message": {"type": "string"}
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    resp = _make_resp({}, status_code=500)
    warnings = check_response(resp, spec, "get", "/items")
    assert any("required field 'message' is missing" in w for w in warnings)


def test_check_response_ref_resolved() -> None:
    """$ref を含むスキーマも正しく解決してチェックされる。"""
    spec: dict[str, Any] = {
        "paths": {
            "/pets": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pet"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {"id": {"type": "integer"}},
                }
            }
        },
    }
    resp = _make_resp({"name": "Fido"})  # id が欠落
    warnings = check_response(resp, spec, "get", "/pets")
    assert any("required field 'id' is missing" in w for w in warnings)


def test_check_response_json_parse_error() -> None:
    """JSON のパースに失敗した場合は警告を返す。"""
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "application/json"}
    resp.json.side_effect = ValueError("invalid json")
    warnings = check_response(resp, SIMPLE_SPEC, "get", "/items")
    assert any("failed to parse" in w for w in warnings)


def test_check_response_range_status_code() -> None:
    """2XX のようなレンジ指定のレスポンス定義を使って検証される。"""
    spec: dict[str, Any] = {
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "2XX": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id"],
                                        "properties": {"id": {"type": "integer"}},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    # 201 は "200" に一致しないが "2XX" にフォールバックされる
    resp = _make_resp({"name": "foo"}, status_code=201)
    warnings = check_response(resp, spec, "get", "/items")
    assert any("required field 'id' is missing" in w for w in warnings)


def test_check_response_with_preparsed_body() -> None:
    """_body を渡すと resp.json() が呼ばれない。"""
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "application/json"}
    # resp.json() が呼ばれたらテスト失敗
    resp.json.side_effect = AssertionError("resp.json() should not be called")
    preparsed = {"id": "not_an_int"}
    warnings = check_response(resp, SIMPLE_SPEC, "get", "/items", _body=preparsed)
    assert any("expected integer" in w for w in warnings)
