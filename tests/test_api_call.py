"""api_call モジュールのテスト."""

from pathlib import Path
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
                {"name": "id", "type": "integer", "required": False},
                {"name": "available", "type": "boolean", "required": False},
                {"name": "price", "type": "number", "required": False},
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
# build_body — 型変換
# ---------------------------------------------------------------------------

POST_PARAMS: list[dict[str, Any]] = [
    {"name": "id", "type": "integer", "required": False},
    {"name": "available", "type": "boolean", "required": False},
    {"name": "price", "type": "number", "required": False},
    {"name": "name", "type": "string", "required": True},
]


def test_build_body_integer_coercion() -> None:
    result = build_body([("id", "42")], POST_PARAMS)
    assert result == {"id": 42}
    assert isinstance(result["id"], int)


def test_build_body_boolean_true_word() -> None:
    result = build_body([("available", "true")], POST_PARAMS)
    assert result == {"available": True}
    assert isinstance(result["available"], bool)


def test_build_body_boolean_false_word() -> None:
    result = build_body([("available", "false")], POST_PARAMS)
    assert result == {"available": False}
    assert isinstance(result["available"], bool)


def test_build_body_boolean_one() -> None:
    result = build_body([("available", "1")], POST_PARAMS)
    assert result == {"available": True}


def test_build_body_boolean_zero() -> None:
    result = build_body([("available", "0")], POST_PARAMS)
    assert result == {"available": False}


def test_build_body_number_coercion() -> None:
    result = build_body([("price", "3.14")], POST_PARAMS)
    assert result == {"price": 3.14}
    assert isinstance(result["price"], float)


def test_build_body_string_unchanged() -> None:
    result = build_body([("name", "Dog")], POST_PARAMS)
    assert result == {"name": "Dog"}
    assert isinstance(result["name"], str)


def test_build_body_invalid_integer_falls_back_to_string(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = build_body([("id", "not-a-number")], POST_PARAMS)
    assert result == {"id": "not-a-number"}
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "integer" in captured.err


def test_build_body_no_post_params_keeps_string() -> None:
    """post_parameters が渡されない場合は型変換しない（後方互換）。"""
    result = build_body([("id", "42")])
    assert result == {"id": "42"}
    assert isinstance(result["id"], str)


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


@rsps.activate
def test_call_api_post_integer_body_param() -> None:
    """call_api が post_parameters の type 情報を使って整数変換する。"""
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={"id": 1}, status=200)
    resp = call_api(
        "post", "/pet", BASE_URL, APIDEF,
        body_params=[("id", "1"), ("name", "My Dog")],
    )
    import json as _json
    body = _json.loads(resp.request.body)  # type: ignore[union-attr]
    assert body["id"] == 1
    assert isinstance(body["id"], int)
    assert body["name"] == "My Dog"


# ---------------------------------------------------------------------------
# _write_log / call_api logging
# ---------------------------------------------------------------------------


@rsps.activate
def test_call_api_writes_log(tmp_path: Path) -> None:
    """logfile が設定されている場合、call_api 後にログが追記される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"dogs": 1}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert "GET" in content
    assert "/store/inventory" in content
    assert "Status: 200" in content
    assert '{"dogs": 1}' in content


@rsps.activate
def test_call_api_log_includes_query_params(tmp_path: Path) -> None:
    """クエリパラメータがログに記録される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api(
        "get", "/store/inventory", BASE_URL, APIDEF,
        query_params=[("status", "available")],
        logfile=logfile,
    )

    content = Path(logfile).read_text(encoding="utf-8")
    assert "available" in content


@rsps.activate
def test_call_api_log_appends(tmp_path: Path) -> None:
    """複数回呼び出すとログが追記される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert content.count("GET") == 2


@rsps.activate
def test_call_api_no_log_when_logfile_none() -> None:
    """logfile が None のときはログファイルを生成しない。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    call_api("get", "/store/inventory", BASE_URL, APIDEF)
    # 例外が起きなければ OK（ファイルシステムへの副作用なし）


@rsps.activate
def test_call_api_log_creates_parent_dir(tmp_path: Path) -> None:
    """ログファイルの親ディレクトリが存在しない場合に自動作成される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "subdir" / "nested" / "test.log")
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    assert Path(logfile).exists()


@rsps.activate
def test_call_api_log_timestamp_has_utc_offset(tmp_path: Path) -> None:
    """ログのタイムスタンプが UTC オフセット付き ISO 8601 形式になっている。"""
    import re as _re
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert _re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", content)


@rsps.activate
def test_call_api_log_masks_authorization_header(tmp_path: Path) -> None:
    """Authorization ヘッダーの値がログ上でマスクされる。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api(
        "get", "/store/inventory", BASE_URL, APIDEF,
        extra_headers=["Authorization: Bearer secret_token"],
        logfile=logfile,
    )

    content = Path(logfile).read_text(encoding="utf-8")
    assert "secret_token" not in content
    assert "***" in content


@rsps.activate
def test_call_api_log_non_sensitive_header_not_masked(tmp_path: Path) -> None:
    """機密でないヘッダーの値はマスクされない。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api(
        "get", "/store/inventory", BASE_URL, APIDEF,
        extra_headers=["X-Custom-Header: visible_value"],
        logfile=logfile,
    )

    content = Path(logfile).read_text(encoding="utf-8")
    assert "visible_value" in content


@rsps.activate
def test_call_api_log_survives_non_serializable_body(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ログの JSON 直列化が失敗しても call_api() は正常終了し、警告を出す。"""
    from unittest.mock import patch

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")

    # フィルターが非シリアライズ可能な body を設定する状況を再現
    with patch("papycli.api_call.json.dumps", side_effect=TypeError("not serializable")):
        resp = call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    assert resp.status_code == 200
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert logfile in captured.err


@rsps.activate
def test_call_api_log_expanduser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """logfile に ~ を含むパスが正しく展開される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    monkeypatch.setenv("HOME", str(tmp_path))
    logfile = "~/test.log"
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    assert (tmp_path / "test.log").exists()


@rsps.activate
def test_call_api_log_uses_pre_filter_values(tmp_path: Path) -> None:
    """ログの先頭セクションにはフィルター適用前の URL・クエリ・ボディが記録される。"""
    from unittest.mock import patch

    from papycli.request_filter import RequestContext

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")

    def mutating_filter(ctx: RequestContext) -> RequestContext:
        return RequestContext(
            method=ctx.method,
            url=ctx.url + "?injected=secret",
            query_params=ctx.query_params + [("injected", "secret")],
            body=ctx.body,
            headers=ctx.headers,
        )

    with patch(
        "papycli.request_filter.load_filters",
        return_value=[("mutating", mutating_filter)],
    ):
        call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    # 先頭の Query 行にはフィルター前の値が記録される（"injected" を含まない）
    query_line = next(line for line in content.splitlines() if line.strip().startswith("Query:"))
    assert "injected" not in query_line
    assert "secret" not in query_line


@rsps.activate
def test_call_api_log_includes_filtered_section_when_filter_applied(tmp_path: Path) -> None:
    """フィルターが 1 件以上適用された場合、Filtered-* セクションがログに追記される。"""
    from unittest.mock import patch

    from papycli.request_filter import RequestContext

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")

    def mutating_filter(ctx: RequestContext) -> RequestContext:
        return RequestContext(
            method=ctx.method,
            url=ctx.url,
            query_params=ctx.query_params + [("added", "value")],
            body=ctx.body,
            headers={**ctx.headers, "X-Added": "yes"},
        )

    with patch(
        "papycli.request_filter.load_filters",
        return_value=[("mutating", mutating_filter)],
    ):
        call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert "Filtered-URL:" in content
    assert "Filtered-Query:" in content
    assert "Filtered-Body:" in content
    assert "Filtered-Headers:" in content
    # フィルター後に追加されたパラメータ・ヘッダーが記録されている
    filtered_query_line = next(
        line for line in content.splitlines() if "Filtered-Query:" in line
    )
    assert "added" in filtered_query_line
    filtered_headers_line = next(
        line for line in content.splitlines() if "Filtered-Headers:" in line
    )
    assert "X-Added" in filtered_headers_line


@rsps.activate
def test_call_api_log_no_filtered_section_without_filters(tmp_path: Path) -> None:
    """フィルターが 0 件の場合、Filtered-* セクションはログに含まれない。"""
    from unittest.mock import patch

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")

    with patch("papycli.request_filter.load_filters", return_value=[]):
        call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert "Filtered-" not in content


@rsps.activate
def test_call_api_log_filtered_headers_masks_sensitive_values(tmp_path: Path) -> None:
    """フィルターが機密ヘッダーを追加した場合、Filtered-Headers でマスクされる。"""
    from unittest.mock import patch

    from papycli.request_filter import RequestContext

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")

    def auth_adding_filter(ctx: RequestContext) -> RequestContext:
        return RequestContext(
            method=ctx.method,
            url=ctx.url,
            query_params=ctx.query_params,
            body=ctx.body,
            headers={**ctx.headers, "Authorization": "Bearer secret_token"},
        )

    with patch(
        "papycli.request_filter.load_filters",
        return_value=[("auth", auth_adding_filter)],
    ):
        call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    filtered_headers_line = next(
        line for line in content.splitlines() if "Filtered-Headers:" in line
    )
    assert "secret_token" not in filtered_headers_line
    assert "***" in filtered_headers_line


@rsps.activate
def test_call_api_log_filtered_section_unserializable_fallback(tmp_path: Path) -> None:
    """フィルター後の値が直列化不可でも、先頭セクションとレスポンスはログに書かれる。"""
    from unittest.mock import patch

    from papycli.request_filter import RequestContext

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"ok": 1}, status=200)
    logfile = str(tmp_path / "test.log")

    def noop_filter(ctx: RequestContext) -> RequestContext:
        return ctx

    # _format_query_str の 2 回目の呼び出し（filtered セクション用）だけ例外を送出させる
    with (
        patch(
            "papycli.request_filter.load_filters",
            return_value=[("noop", noop_filter)],
        ),
        patch(
            "papycli.api_call._format_query_str",
            side_effect=["(none)", TypeError("simulated serialization error")],
        ),
    ):
        call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    # 先頭セクションとレスポンスは書かれている
    assert "GET" in content
    assert "Status: 200" in content
    # Filtered-* はフォールバック値になっている
    assert "(unserializable)" in content


@rsps.activate
def test_call_api_log_filtered_section_unserializable_emits_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """フィルター後の値が直列化不可の場合、警告を stderr に出力する。"""
    from unittest.mock import patch

    from papycli.request_filter import RequestContext

    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)
    logfile = str(tmp_path / "test.log")

    def noop_filter(ctx: RequestContext) -> RequestContext:
        return ctx

    with (
        patch(
            "papycli.request_filter.load_filters",
            return_value=[("noop", noop_filter)],
        ),
        patch(
            "papycli.api_call._format_query_str",
            side_effect=["(none)", TypeError("simulated serialization error")],
        ),
    ):
        call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    assert "Warning" in capsys.readouterr().err


@rsps.activate
def test_call_api_log_truncates_large_response(tmp_path: Path) -> None:
    """レスポンスボディが大きい場合にログで切り詰められる。"""
    from papycli.api_call import _LOG_BODY_MAX_CHARS

    large_body = "x" * (_LOG_BODY_MAX_CHARS + 1000)
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", body=large_body, status=200,
             content_type="text/plain")
    logfile = str(tmp_path / "test.log")
    call_api("get", "/store/inventory", BASE_URL, APIDEF, logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert "...[truncated]" in content


@rsps.activate
def test_call_api_log_truncates_large_request_body(tmp_path: Path) -> None:
    """リクエストボディが大きい場合にログで切り詰められる。"""
    from papycli.api_call import _LOG_BODY_MAX_CHARS

    large_value = "y" * (_LOG_BODY_MAX_CHARS + 1000)
    rsps.add(rsps.POST, f"{BASE_URL}/pet", json={}, status=200)
    logfile = str(tmp_path / "test.log")
    call_api("post", "/pet", BASE_URL, APIDEF, raw_body=f'"{large_value}"', logfile=logfile)

    content = Path(logfile).read_text(encoding="utf-8")
    assert "...[truncated]" in content
