"""api_call モジュールのテスト."""

from typing import Any

import pytest
import responses as rsps

from papycli.api_call import (
    build_body,
    call_api,
    expand_path,
    match_path_template,
    parse_headers,
)

# ---------------------------------------------------------------------------
# テスト用 apidef
# ---------------------------------------------------------------------------

APIDEF: dict[str, Any] = {
    "/store/inventory": [
        {"method": "get", "query_parameters": [], "post_parameters": []}
    ],
    "/pet/findByStatus": [
        {
            "method": "get",
            "query_parameters": [
                {"name": "status", "type": "string", "required": False,
                 "enum": ["available", "pending", "sold"]}
            ],
            "post_parameters": [],
        }
    ],
    "/pet": [
        {
            "method": "post",
            "query_parameters": [],
            "post_parameters": [
                {"name": "name", "type": "string", "required": True},
                {"name": "status", "type": "string", "required": False},
            ],
        },
        {"method": "put", "query_parameters": [], "post_parameters": []},
    ],
    "/pet/{petId}": [
        {"method": "get", "query_parameters": [], "post_parameters": []},
        {"method": "delete", "query_parameters": [], "post_parameters": []},
    ],
}

BASE_URL = "http://localhost:8080/api/v3"


# ---------------------------------------------------------------------------
# match_path_template
# ---------------------------------------------------------------------------


def test_match_exact() -> None:
    result = match_path_template("/store/inventory", list(APIDEF.keys()))
    assert result is not None
    template, params = result
    assert template == "/store/inventory"
    assert params == {}


def test_match_exact_preferred_over_template() -> None:
    """完全一致がテンプレートより優先される。"""
    result = match_path_template("/pet/findByStatus", list(APIDEF.keys()))
    assert result is not None
    template, params = result
    assert template == "/pet/findByStatus"
    assert params == {}


def test_match_template_with_path_param() -> None:
    result = match_path_template("/pet/99", list(APIDEF.keys()))
    assert result is not None
    template, params = result
    assert template == "/pet/{petId}"
    assert params == {"petId": "99"}


def test_match_template_string_id() -> None:
    result = match_path_template("/pet/some-name", list(APIDEF.keys()))
    assert result is not None
    template, _ = result
    assert template == "/pet/{petId}"


def test_match_no_match() -> None:
    result = match_path_template("/nonexistent", list(APIDEF.keys()))
    assert result is None


def test_match_root_exact() -> None:
    templates = ["/pet", "/pet/{petId}"]
    result = match_path_template("/pet", templates)
    assert result is not None
    assert result[0] == "/pet"


# ---------------------------------------------------------------------------
# expand_path
# ---------------------------------------------------------------------------


def test_expand_path_single_param() -> None:
    assert expand_path("/pet/{petId}", {"petId": "99"}) == "/pet/99"


def test_expand_path_multiple_params() -> None:
    assert expand_path("/a/{x}/b/{y}", {"x": "foo", "y": "bar"}) == "/a/foo/b/bar"


def test_expand_path_no_params() -> None:
    assert expand_path("/store/inventory", {}) == "/store/inventory"


# ---------------------------------------------------------------------------
# build_body
# ---------------------------------------------------------------------------


def test_build_body_simple() -> None:
    result = build_body([("name", "Dog"), ("status", "available")])
    assert result == {"name": "Dog", "status": "available"}


def test_build_body_repeated_key_becomes_array() -> None:
    result = build_body([("tags", "foo"), ("tags", "bar")])
    assert result == {"tags": ["foo", "bar"]}


def test_build_body_dot_notation() -> None:
    result = build_body([("category.id", "1"), ("category.name", "Dogs")])
    assert result == {"category": {"id": "1", "name": "Dogs"}}


def test_build_body_dot_notation_repeated() -> None:
    result = build_body([("tags.name", "x"), ("tags.name", "y")])
    assert result == {"tags": {"name": ["x", "y"]}}


def test_build_body_mixed() -> None:
    result = build_body([
        ("id", "1"),
        ("name", "Dog"),
        ("photoUrls", "http://a.jpg"),
        ("photoUrls", "http://b.jpg"),
        ("category.id", "2"),
        ("category.name", "Hounds"),
    ])
    assert result["id"] == "1"
    assert result["name"] == "Dog"
    assert result["photoUrls"] == ["http://a.jpg", "http://b.jpg"]
    assert result["category"] == {"id": "2", "name": "Hounds"}


def test_build_body_empty() -> None:
    assert build_body([]) == {}


# ---------------------------------------------------------------------------
# parse_headers
# ---------------------------------------------------------------------------


def test_parse_headers_single() -> None:
    result = parse_headers(["Authorization: Bearer token"])
    assert result == {"Authorization": "Bearer token"}


def test_parse_headers_multiple() -> None:
    result = parse_headers(["X-Foo: bar", "X-Baz: qux"])
    assert result == {"X-Foo": "bar", "X-Baz": "qux"}


def test_parse_headers_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    result = parse_headers([], "Authorization: Bearer tok\nX-Tenant: acme")
    assert result == {"Authorization": "Bearer tok", "X-Tenant": "acme"}


def test_parse_headers_cli_overrides_env() -> None:
    result = parse_headers(["Authorization: Bearer new"], "Authorization: Bearer old")
    assert result["Authorization"] == "Bearer new"


def test_parse_headers_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid header format"):
        parse_headers(["BadHeader"])


def test_parse_headers_value_with_colon() -> None:
    """ヘッダー値にコロンが含まれる場合（例: URL）も正しく解析できる。"""
    result = parse_headers(["Location: http://example.com/path"])
    assert result == {"Location": "http://example.com/path"}


# ---------------------------------------------------------------------------
# call_api — HTTP モックテスト
# ---------------------------------------------------------------------------


@rsps.activate
def test_call_api_get_simple() -> None:
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"dogs": 1}, status=200)
    resp = call_api("get", "/store/inventory", BASE_URL, APIDEF)
    assert resp.status_code == 200
    assert resp.json() == {"dogs": 1}


@rsps.activate
def test_call_api_get_with_query_params() -> None:
    rsps.add(rsps.GET, f"{BASE_URL}/pet/findByStatus", json=[], status=200)
    resp = call_api(
        "get", "/pet/findByStatus", BASE_URL, APIDEF,
        query_params=[("status", "available")],
    )
    assert resp.status_code == 200
    assert "status=available" in resp.request.url  # type: ignore[union-attr]


@rsps.activate
def test_call_api_get_with_path_param() -> None:
    rsps.add(rsps.GET, f"{BASE_URL}/pet/99", json={"id": 99}, status=200)
    resp = call_api("get", "/pet/99", BASE_URL, APIDEF)
    assert resp.status_code == 200
    assert resp.request.url == f"{BASE_URL}/pet/99"  # type: ignore[union-attr]


@rsps.activate
def test_call_api_post_with_body_params() -> None:
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)
    resp = call_api(
        "post", "/pet", BASE_URL, APIDEF,
        body_params=[("name", "My Dog"), ("status", "available")],
    )
    assert resp.status_code == 200
    sent = resp.request  # type: ignore[union-attr]
    import json
    body = json.loads(sent.body)
    assert body == {"name": "My Dog", "status": "available"}


@rsps.activate
def test_call_api_post_with_raw_body() -> None:
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)
    resp = call_api(
        "post", "/pet", BASE_URL, APIDEF,
        raw_body='{"name": "Dog", "status": "available", "photoUrls": []}',
    )
    assert resp.status_code == 200


@rsps.activate
def test_call_api_delete_with_path_param() -> None:
    rsps.add(rsps.DELETE, f"{BASE_URL}/pet/1", status=204)
    resp = call_api("delete", "/pet/1", BASE_URL, APIDEF)
    assert resp.status_code == 204


@rsps.activate
def test_call_api_custom_header() -> None:
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    resp = call_api(
        "get", "/store/inventory", BASE_URL, APIDEF,
        extra_headers=["X-Custom: myvalue"],
    )
    assert resp.request.headers["X-Custom"] == "myvalue"  # type: ignore[union-attr]


def test_call_api_no_base_url() -> None:
    with pytest.raises(RuntimeError, match="Base URL"):
        call_api("get", "/store/inventory", "", APIDEF)


def test_call_api_unknown_path() -> None:
    with pytest.raises(ValueError, match="No matching path"):
        call_api("get", "/unknown/path", BASE_URL, APIDEF)


def test_call_api_wrong_method() -> None:
    with pytest.raises(ValueError, match="not defined"):
        call_api("patch", "/store/inventory", BASE_URL, APIDEF)
