"""checker モジュールのテスト。"""

from typing import Any

import pytest

from papycli.checker import check_request

# ---------------------------------------------------------------------------
# テスト用 apidef
# ---------------------------------------------------------------------------

APIDEF: dict[str, Any] = {
    "/pet": [
        {
            "method": "post",
            "query_parameters": [],
            "post_parameters": [
                {"name": "name", "type": "string", "required": True},
                {"name": "status", "type": "string", "required": False,
                 "enum": ["available", "pending", "sold"]},
                {"name": "photoUrls", "type": "array", "required": True},
                {"name": "age", "type": "integer", "required": False},
            ],
        }
    ],
    "/pet/findByStatus": [
        {
            "method": "get",
            "query_parameters": [
                {"name": "status", "type": "string", "required": True,
                 "enum": ["available", "pending", "sold"]},
                {"name": "limit", "type": "integer", "required": False},
            ],
            "post_parameters": [],
        }
    ],
    "/toggle": [
        {
            "method": "post",
            "query_parameters": [],
            "post_parameters": [
                {"name": "enabled", "type": "boolean", "required": True},
            ],
        }
    ],
    "/pet/{petId}": [
        {"method": "get", "query_parameters": [], "post_parameters": []},
    ],
}


def chk(
    method: str,
    resource: str,
    query_params: list[tuple[str, str]] | None = None,
    body_params: list[tuple[str, str]] | None = None,
    raw_body: str | None = None,
) -> list[str]:
    return check_request(
        APIDEF, method, resource,
        query_params or [],
        body_params or [],
        raw_body,
    )


# ---------------------------------------------------------------------------
# 必須パラメータの存在チェック
# ---------------------------------------------------------------------------


def test_missing_required_body_param() -> None:
    warnings = chk("post", "/pet", body_params=[("name", "Rex")])
    # photoUrls (required) が不足
    assert any("photoUrls" in w for w in warnings)


def test_all_required_body_params_present() -> None:
    warnings = chk("post", "/pet", body_params=[
        ("name", "Rex"), ("photoUrls", "http://example.com/a.jpg")
    ])
    assert not any("missing" in w for w in warnings)


def test_missing_required_query_param() -> None:
    warnings = chk("get", "/pet/findByStatus")
    assert any("status" in w and "missing" in w for w in warnings)


def test_required_query_param_present() -> None:
    warnings = chk("get", "/pet/findByStatus", query_params=[("status", "available")])
    assert not any("missing" in w for w in warnings)


# ---------------------------------------------------------------------------
# enum チェック
# ---------------------------------------------------------------------------


def test_enum_violation_body() -> None:
    warnings = chk("post", "/pet", body_params=[
        ("name", "Rex"), ("photoUrls", "url"), ("status", "unknown")
    ])
    assert any("status" in w and "enum" in w for w in warnings)


def test_enum_valid_body() -> None:
    warnings = chk("post", "/pet", body_params=[
        ("name", "Rex"), ("photoUrls", "url"), ("status", "available")
    ])
    assert not any("enum" in w for w in warnings)


def test_enum_violation_query() -> None:
    warnings = chk("get", "/pet/findByStatus", query_params=[("status", "bad")])
    assert any("status" in w and "enum" in w for w in warnings)


# ---------------------------------------------------------------------------
# 型チェック
# ---------------------------------------------------------------------------


def test_type_integer_invalid() -> None:
    warnings = chk("post", "/pet", body_params=[
        ("name", "Rex"), ("photoUrls", "url"), ("age", "notanumber")
    ])
    assert any("age" in w and "integer" in w for w in warnings)


def test_type_integer_valid() -> None:
    warnings = chk("post", "/pet", body_params=[
        ("name", "Rex"), ("photoUrls", "url"), ("age", "5")
    ])
    assert not any("age" in w and "integer" in w for w in warnings)


def test_type_boolean_invalid() -> None:
    warnings = chk("post", "/toggle", body_params=[("enabled", "yes")])
    assert any("enabled" in w and "boolean" in w for w in warnings)


def test_type_boolean_valid_true() -> None:
    warnings = chk("post", "/toggle", body_params=[("enabled", "true")])
    assert not any("boolean" in w for w in warnings)


def test_type_boolean_valid_false() -> None:
    warnings = chk("post", "/toggle", body_params=[("enabled", "false")])
    assert not any("boolean" in w for w in warnings)


def test_type_integer_query() -> None:
    warnings = chk("get", "/pet/findByStatus", query_params=[
        ("status", "available"), ("limit", "abc")
    ])
    assert any("limit" in w and "integer" in w for w in warnings)


# ---------------------------------------------------------------------------
# -d raw_body のチェック
# ---------------------------------------------------------------------------


def test_raw_body_missing_required() -> None:
    import json
    body = json.dumps({"name": "Rex"})  # photoUrls 欠落
    warnings = chk("post", "/pet", raw_body=body)
    assert any("photoUrls" in w and "missing" in w for w in warnings)


def test_raw_body_enum_violation() -> None:
    import json
    body = json.dumps({"name": "Rex", "photoUrls": [], "status": "bad"})
    warnings = chk("post", "/pet", raw_body=body)
    assert any("status" in w and "enum" in w for w in warnings)


def test_raw_body_invalid_json() -> None:
    warnings = chk("post", "/pet", raw_body="not-json")
    assert any("JSON" in w for w in warnings)
    # parse 失敗後は "missing" 警告を出さない（ノイズを避けるため早期 return）
    assert not any("missing" in w for w in warnings)


def test_raw_body_non_dict_json() -> None:
    # JSON 配列や数値などの非 dict 値は AttributeError にならず警告を返す
    warnings = chk("post", "/pet", raw_body="[1, 2, 3]")
    assert any("not a JSON object" in w for w in warnings)

    warnings2 = chk("post", "/pet", raw_body="42")
    assert any("not a JSON object" in w for w in warnings2)


# ---------------------------------------------------------------------------
# パス不明・メソッド不明はエラーなし（api_call 側に委ねる）
# ---------------------------------------------------------------------------


def test_unknown_resource_no_warnings() -> None:
    warnings = chk("get", "/unknown/path")
    assert warnings == []


def test_path_template_match() -> None:
    # /pet/99 → /pet/{petId} にマッチ、GET はパラメータなし → 警告なし
    warnings = chk("get", "/pet/99")
    assert warnings == []
