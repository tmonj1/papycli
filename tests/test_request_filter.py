"""request_filter モジュールのテスト."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import responses as rsps

from papycli.api_call import call_api
from papycli.request_filter import (
    RequestContext,
    ResponseContext,
    apply_filters,
    apply_response_filters,
    load_filters,
    load_response_filters,
)

# ---------------------------------------------------------------------------
# RequestContext
# ---------------------------------------------------------------------------


def test_request_context_defaults() -> None:
    ctx = RequestContext(method="get", url="http://example.com/api")
    assert ctx.query_params == []
    assert ctx.body is None
    assert ctx.headers == {}


def test_request_context_fields() -> None:
    ctx = RequestContext(
        method="post",
        url="http://example.com/pet",
        query_params=[("status", "available")],
        body={"name": "Dog"},
        headers={"Authorization": "Bearer token"},
    )
    assert ctx.method == "post"
    assert ctx.url == "http://example.com/pet"
    assert ctx.query_params == [("status", "available")]
    assert ctx.body == {"name": "Dog"}
    assert ctx.headers == {"Authorization": "Bearer token"}


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------


def _add_header_filter(ctx: RequestContext) -> RequestContext:
    ctx.headers["X-Added"] = "yes"
    return ctx


def _modify_url_filter(ctx: RequestContext) -> RequestContext:
    ctx.url = ctx.url + "/modified"
    return ctx


def _add_query_filter(ctx: RequestContext) -> RequestContext:
    ctx.query_params.append(("injected", "value"))
    return ctx


def _modify_body_filter(ctx: RequestContext) -> RequestContext:
    if isinstance(ctx.body, dict):
        ctx.body["extra"] = "added"
    return ctx


def _raising_filter(ctx: RequestContext) -> RequestContext:
    raise RuntimeError("filter exploded")


def test_apply_filters_empty() -> None:
    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(ctx, [])
    assert result.url == "http://example.com/"


def test_apply_filters_single_header() -> None:
    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(ctx, [("my-filter", _add_header_filter)])
    assert result.headers["X-Added"] == "yes"


def test_apply_filters_modifies_url() -> None:
    ctx = RequestContext(method="get", url="http://example.com/api")
    result = apply_filters(ctx, [("url-filter", _modify_url_filter)])
    assert result.url == "http://example.com/api/modified"


def test_apply_filters_modifies_query_params() -> None:
    ctx = RequestContext(method="get", url="http://example.com/", query_params=[("a", "1")])
    result = apply_filters(ctx, [("q-filter", _add_query_filter)])
    assert ("injected", "value") in result.query_params
    assert ("a", "1") in result.query_params


def test_apply_filters_modifies_body() -> None:
    ctx = RequestContext(method="post", url="http://example.com/", body={"name": "Dog"})
    result = apply_filters(ctx, [("body-filter", _modify_body_filter)])
    assert result.body == {"name": "Dog", "extra": "added"}  # type: ignore[index]


def test_apply_filters_chained_order() -> None:
    """フィルターは登録順（プラグイン名昇順）に適用される。"""
    log: list[str] = []

    def filter_a(ctx: RequestContext) -> RequestContext:
        log.append("a")
        return ctx

    def filter_b(ctx: RequestContext) -> RequestContext:
        log.append("b")
        return ctx

    ctx = RequestContext(method="get", url="http://example.com/")
    apply_filters(ctx, [("a-filter", filter_a), ("b-filter", filter_b)])
    assert log == ["a", "b"]


def test_apply_filters_skips_raising_filter(capsys: pytest.CaptureFixture[str]) -> None:
    """例外を送出したフィルターはスキップされ、後続フィルターの処理は続く。"""
    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(
        ctx,
        [("bad-filter", _raising_filter), ("good-filter", _add_header_filter)],
    )
    # 後続フィルターは実行される
    assert result.headers.get("X-Added") == "yes"
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "bad-filter" in captured.err


def test_apply_filters_all_raising(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(ctx, [("f1", _raising_filter), ("f2", _raising_filter)])
    # ctx は変更なし
    assert result.url == "http://example.com/"
    captured = capsys.readouterr()
    assert captured.err.count("Warning") == 2


def test_apply_filters_invalid_return_type_skipped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """RequestContext 以外を返したフィルターはスキップされ、前の ctx を維持する。"""
    def bad_return(ctx: RequestContext) -> RequestContext:
        return None  # type: ignore[return-value]

    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(
        ctx,
        [("bad-return", bad_return), ("good-filter", _add_header_filter)],
    )
    # bad-return はスキップ、good-filter は実行される
    assert result.headers.get("X-Added") == "yes"
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "bad-return" in captured.err


def test_apply_filters_inplace_mutation_before_raise_is_reverted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """フィルターが例外を送出する前にインプレース変更しても、後続フィルターには反映されない。"""
    def mutate_then_raise(ctx: RequestContext) -> RequestContext:
        ctx.headers["X-Leaked"] = "leaked"
        raise RuntimeError("oops")

    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(ctx, [("bad-filter", mutate_then_raise)])
    # 変更はキャンセルされる
    assert "X-Leaked" not in result.headers
    captured = capsys.readouterr()
    assert "Warning" in captured.err


def test_apply_filters_inplace_mutation_before_bad_return_is_reverted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """フィルターが不正な戻り値を返す前にインプレース変更しても、後続フィルターには反映されない。"""
    def mutate_then_bad_return(ctx: RequestContext) -> RequestContext:
        ctx.headers["X-Leaked"] = "leaked"
        return None  # type: ignore[return-value]

    ctx = RequestContext(method="get", url="http://example.com/")
    result = apply_filters(ctx, [("bad-filter", mutate_then_bad_return)])
    assert "X-Leaked" not in result.headers


# ---------------------------------------------------------------------------
# load_filters
# ---------------------------------------------------------------------------


def _make_ep(name: str, func: Any) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = func
    return ep


def test_load_filters_empty() -> None:
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[]):
        result = load_filters()
    assert result == []


def test_load_filters_sorted_by_name() -> None:
    eps = [
        _make_ep("z-filter", _add_header_filter),
        _make_ep("a-filter", _modify_url_filter),
        _make_ep("m-filter", _add_query_filter),
    ]
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=eps):
        result = load_filters()
    names = [name for name, _ in result]
    assert names == ["a-filter", "m-filter", "z-filter"]


def test_load_filters_skips_failing_load(capsys: pytest.CaptureFixture[str]) -> None:
    bad_ep = MagicMock()
    bad_ep.name = "bad-plugin"
    bad_ep.load.side_effect = ImportError("module not found")
    good_ep = _make_ep("good-plugin", _add_header_filter)

    with patch(
        "papycli.request_filter.importlib.metadata.entry_points",
        return_value=[bad_ep, good_ep],
    ):
        result = load_filters()

    names = [name for name, _ in result]
    assert "bad-plugin" not in names
    assert "good-plugin" in names
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "bad-plugin" in captured.err


def test_load_filters_skips_non_callable(capsys: pytest.CaptureFixture[str]) -> None:
    """callable でないエントリポイントはロード時点でスキップされる。"""
    bad_ep = MagicMock()
    bad_ep.name = "non-callable-plugin"
    bad_ep.load.return_value = "not_a_function"
    good_ep = _make_ep("good-plugin", _add_header_filter)

    with patch(
        "papycli.request_filter.importlib.metadata.entry_points",
        return_value=[bad_ep, good_ep],
    ):
        result = load_filters()

    names = [name for name, _ in result]
    assert "non-callable-plugin" not in names
    assert "good-plugin" in names
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "non-callable-plugin" in captured.err


# ---------------------------------------------------------------------------
# call_api との統合テスト
# ---------------------------------------------------------------------------

APIDEF: dict[str, Any] = {
    "/pet": [
        {
            "method": "post",
            "query_parameters": [],
            "post_parameters": [
                {"name": "name", "type": "string", "required": True},
            ],
        }
    ],
    "/store/inventory": [
        {"method": "get", "query_parameters": [], "post_parameters": []}
    ],
}
BASE_URL = "http://localhost:8080/api/v3"


@rsps.activate
def test_call_api_filter_adds_header() -> None:
    """フィルターが追加したヘッダーがリクエストに反映される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)

    def inject_header(ctx: RequestContext) -> RequestContext:
        ctx.headers["X-Filter"] = "injected"
        return ctx

    ep = _make_ep("h-filter", inject_header)
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[ep]):
        resp = call_api("get", "/store/inventory", BASE_URL, APIDEF)

    assert resp.request.headers["X-Filter"] == "injected"  # type: ignore[union-attr]


@rsps.activate
def test_call_api_filter_modifies_query_params() -> None:
    """フィルターが追加したクエリパラメータがリクエストに反映される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={}, status=200)

    def inject_query(ctx: RequestContext) -> RequestContext:
        ctx.query_params.append(("token", "abc"))
        return ctx

    ep = _make_ep("q-filter", inject_query)
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[ep]):
        resp = call_api("get", "/store/inventory", BASE_URL, APIDEF)

    assert "token=abc" in resp.request.url  # type: ignore[union-attr]


@rsps.activate
def test_call_api_no_filters() -> None:
    """フィルターが 0 件のときも通常通りリクエストが送信される。"""
    rsps.add(rsps.GET, f"{BASE_URL}/store/inventory", json={"dogs": 1}, status=200)

    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[]):
        resp = call_api("get", "/store/inventory", BASE_URL, APIDEF)

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# ResponseContext
# ---------------------------------------------------------------------------


def test_response_context_defaults() -> None:
    ctx = ResponseContext(method="get", url="http://example.com/api", status_code=200, reason="OK")
    assert ctx.headers == {}
    assert ctx.body is None
    assert ctx.request_body is None


def test_response_context_fields() -> None:
    ctx = ResponseContext(
        method="get",
        url="http://example.com/api",
        status_code=404,
        reason="Not Found",
        headers={"Content-Type": "application/json"},
        body={"error": "not found"},
    )
    assert ctx.status_code == 404
    assert ctx.reason == "Not Found"
    assert ctx.body == {"error": "not found"}


def test_response_context_request_body() -> None:
    ctx = ResponseContext(
        method="post",
        url="http://example.com/api/pet",
        status_code=200,
        reason="OK",
        body={"id": 1},
        request_body={"name": "Fido", "status": "available"},
    )
    assert ctx.request_body == {"name": "Fido", "status": "available"}


# ---------------------------------------------------------------------------
# load_response_filters
# ---------------------------------------------------------------------------


def test_load_response_filters_empty() -> None:
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[]):
        result = load_response_filters()
    assert result == []


def test_load_response_filters_load_error_skipped(capsys: pytest.CaptureFixture[str]) -> None:
    ep = MagicMock()
    ep.name = "bad-filter"
    ep.load.side_effect = ImportError("missing module")
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[ep]):
        result = load_response_filters()
    assert result == []
    assert "Warning" in capsys.readouterr().err


def test_load_response_filters_skips_non_callable(capsys: pytest.CaptureFixture[str]) -> None:
    ep = MagicMock()
    ep.name = "non-callable"
    ep.load.return_value = "not a function"
    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[ep]):
        result = load_response_filters()
    assert result == []
    assert "Warning" in capsys.readouterr().err


def test_load_response_filters_sorted_by_name() -> None:
    def f1(ctx: ResponseContext) -> ResponseContext:
        return ctx

    def f2(ctx: ResponseContext) -> ResponseContext:
        return ctx

    ep1 = MagicMock()
    ep1.name = "z-filter"
    ep1.load.return_value = f1
    ep2 = MagicMock()
    ep2.name = "a-filter"
    ep2.load.return_value = f2

    with patch("papycli.request_filter.importlib.metadata.entry_points", return_value=[ep1, ep2]):
        result = load_response_filters()

    assert [name for name, _ in result] == ["a-filter", "z-filter"]


# ---------------------------------------------------------------------------
# apply_response_filters
# ---------------------------------------------------------------------------


def test_apply_response_filters_empty() -> None:
    ctx = ResponseContext(method="get", url="http://example.com", status_code=200, reason="OK",
                         body={"k": "v"})
    result = apply_response_filters(ctx, [])
    assert result.body == {"k": "v"}


def test_apply_response_filters_modifies_body() -> None:
    def add_field(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["added"] = True
        return ctx

    ctx = ResponseContext(method="get", url="http://example.com", status_code=200, reason="OK",
                         body={"original": 1})
    result = apply_response_filters(ctx, [("add-field", add_field)])
    assert result.body == {"original": 1, "added": True}


def test_apply_response_filters_chained() -> None:
    def double_value(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["value"] = ctx.body["value"] * 2
        return ctx

    ctx = ResponseContext(method="get", url="http://example.com", status_code=200, reason="OK",
                         body={"value": 3})
    result = apply_response_filters(ctx, [("f1", double_value), ("f2", double_value)])
    assert result.body == {"value": 12}


def test_apply_response_filters_snapshot_prevents_inplace_leak() -> None:
    """フィルターが例外前にインプレース変更しても、前の ctx が維持される。"""
    def mutate_then_raise(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["leaked"] = True
        raise RuntimeError("oops")

    ctx = ResponseContext(method="get", url="http://example.com", status_code=200, reason="OK",
                         body={"original": 1})
    result = apply_response_filters(ctx, [("bad", mutate_then_raise)])
    assert result.body == {"original": 1}
    assert "leaked" not in (result.body or {})


def test_apply_response_filters_exception_skipped(capsys: pytest.CaptureFixture[str]) -> None:
    def bad(ctx: ResponseContext) -> ResponseContext:
        raise ValueError("error")

    ctx = ResponseContext(method="get", url="http://example.com", status_code=200, reason="OK",
                         body="original")
    result = apply_response_filters(ctx, [("bad", bad)])
    assert result.body == "original"
    assert "Warning" in capsys.readouterr().err


def test_apply_response_filters_wrong_return_type_skipped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def bad(ctx: ResponseContext) -> Any:
        return {"not": "a ResponseContext"}

    ctx = ResponseContext(method="get", url="http://example.com", status_code=200, reason="OK",
                         body="original")
    result = apply_response_filters(ctx, [("bad", bad)])
    assert result.body == "original"
    assert "Warning" in capsys.readouterr().err


def test_apply_response_filters_request_body_passed_to_filter() -> None:
    """フィルターが request_body を参照できる。"""
    received: list[Any] = []

    def capture(ctx: ResponseContext) -> ResponseContext:
        received.append(ctx.request_body)
        return ctx

    ctx = ResponseContext(
        method="post",
        url="http://example.com/api/pet",
        status_code=200,
        reason="OK",
        body={"id": 1},
        request_body={"name": "Fido"},
    )
    apply_response_filters(ctx, [("capture", capture)])
    assert received == [{"name": "Fido"}]


def test_apply_response_filters_request_body_snapshot_isolated() -> None:
    """スナップショットの request_body はディープコピーされ、変更が元 ctx に漏れない。"""
    def mutate_then_raise(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.request_body, dict)
        ctx.request_body["leaked"] = True
        raise RuntimeError("oops")

    ctx = ResponseContext(
        method="post",
        url="http://example.com/api/pet",
        status_code=200,
        reason="OK",
        body={"id": 1},
        request_body={"name": "Fido"},
    )
    result = apply_response_filters(ctx, [("bad", mutate_then_raise)])
    assert result.request_body == {"name": "Fido"}
    assert "leaked" not in (result.request_body or {})


def test_apply_response_filters_request_body_immutable() -> None:
    """フィルターが request_body を変更しても、後続フィルターと最終結果には元の値が維持される。"""
    received: list[Any] = []

    def mutate(ctx: ResponseContext) -> ResponseContext:
        ctx.request_body = {"mutated": True}
        return ctx

    def capture(ctx: ResponseContext) -> ResponseContext:
        received.append(ctx.request_body)
        return ctx

    ctx = ResponseContext(
        method="post",
        url="http://example.com/api/pet",
        status_code=200,
        reason="OK",
        body={"id": 1},
        request_body={"name": "Fido"},
    )
    result = apply_response_filters(ctx, [("mutate", mutate), ("capture", capture)])
    # 後続フィルターには元の request_body が渡される
    assert received == [{"name": "Fido"}]
    # 最終結果も元の request_body が維持される
    assert result.request_body == {"name": "Fido"}


# ---------------------------------------------------------------------------
# call_api とレスポンスフィルターの統合
# ---------------------------------------------------------------------------


BASE_URL_RF = "http://petstore.example.com"
APIDEF_RF: dict[str, Any] = {
    "/store/inventory": [{"method": "get", "query_parameters": [], "post_parameters": []}],
    "/pet": [{"method": "post", "query_parameters": [], "post_parameters": [
        {"name": "name", "type": "string", "required": True},
    ]}],
}


@pytest.fixture(autouse=False)
def no_request_filters() -> Any:
    """call_api integration tests: リクエストフィルターを空にして hermetic にする。"""
    with patch("papycli.request_filter.load_filters", return_value=[]):
        yield


@rsps.activate
def test_call_api_response_filter_modifies_body(no_request_filters: Any) -> None:
    """レスポンスフィルターがボディを変更すると resp._content に反映される。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    def add_cats(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["cats"] = 99
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("add-cats", add_cats)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert resp.json() == {"dogs": 1, "cats": 99}


@rsps.activate
def test_call_api_response_filter_receives_correct_context(no_request_filters: Any) -> None:
    """ResponseContext に method・url・status_code・reason が正しく渡される。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={}, status=200)
    received: list[ResponseContext] = []

    def capture(ctx: ResponseContext) -> ResponseContext:
        received.append(ctx)
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("capture", capture)]):
        call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert len(received) == 1
    ctx = received[0]
    assert ctx.method == "get"
    assert ctx.status_code == 200
    assert ctx.reason == "OK"
    assert "/store/inventory" in ctx.url
    assert ctx.request_body is None  # GET リクエストなのでボディなし


@rsps.activate
def test_call_api_response_filter_receives_request_body(no_request_filters: Any) -> None:
    """POST リクエストのボディが ResponseContext.request_body に渡される。"""
    rsps.add(rsps.POST, f"{BASE_URL_RF}/pet", json={"id": 1}, status=200)
    received: list[ResponseContext] = []

    def capture(ctx: ResponseContext) -> ResponseContext:
        received.append(ctx)
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("capture", capture)]):
        call_api("post", "/pet", BASE_URL_RF, APIDEF_RF, body_params=[("name", "Fido")])

    assert len(received) == 1
    assert received[0].request_body == {"name": "Fido"}


@rsps.activate
def test_call_api_response_filter_body_set_to_none(no_request_filters: Any) -> None:
    """フィルターが body を None にすると resp._content が空になる。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    def clear_body(ctx: ResponseContext) -> ResponseContext:
        ctx.body = None
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("clear", clear_body)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert resp.content == b""


@rsps.activate
def test_call_api_response_filter_no_filters_unchanged(no_request_filters: Any) -> None:
    """レスポンスフィルターが 0 件のとき、レスポンスは変更されない。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    with patch("papycli.request_filter.load_response_filters", return_value=[]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert resp.json() == {"dogs": 1}


@rsps.activate
def test_call_api_response_filter_noop_body_not_rewritten(no_request_filters: Any) -> None:
    """フィルターがボディを論理的に変更しない場合、_content は書き換えられない。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    def noop(ctx: ResponseContext) -> ResponseContext:
        # ボディを等価な値で上書きするが変更はない
        ctx.body = {"dogs": 1}
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("noop", noop)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    # モックが返した元のレスポンスボディ（生バイト列）
    original_bytes = rsps.calls[0].response.content
    # _content は書き換えられておらず、元のバイト列のまま
    assert resp.content == original_bytes
    # かつ、JSON としての値も正しく読める
    assert resp.json() == {"dogs": 1}


@rsps.activate
def test_call_api_response_filter_modifies_status_code(no_request_filters: Any) -> None:
    """フィルターが status_code を変更すると resp.status_code に反映される。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={}, status=200)

    def change_status(ctx: ResponseContext) -> ResponseContext:
        ctx.status_code = 201
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("s", change_status)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert resp.status_code == 201


@rsps.activate
def test_call_api_response_filter_modifies_reason(no_request_filters: Any) -> None:
    """フィルターが reason を変更すると resp.reason に反映される。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={}, status=200)

    def change_reason(ctx: ResponseContext) -> ResponseContext:
        ctx.reason = "Custom Reason"
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("r", change_reason)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert resp.reason == "Custom Reason"


@rsps.activate
def test_call_api_response_filter_modifies_headers(no_request_filters: Any) -> None:
    """フィルターが headers を変更すると resp.headers に反映される。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={}, status=200)

    def add_header(ctx: ResponseContext) -> ResponseContext:
        ctx.headers["X-Custom"] = "value"
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("h", add_header)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert resp.headers["X-Custom"] == "value"


@rsps.activate
def test_call_api_response_filter_non_serializable_body_warns(
    capsys: pytest.CaptureFixture[str],
    no_request_filters: Any,
) -> None:
    """フィルターが非シリアライズ可能な値をボディに設定した場合、警告を出し元レスポンスを維持する。"""
    import datetime

    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    def bad_body(ctx: ResponseContext) -> ResponseContext:
        ctx.body = {"ts": datetime.datetime.now()}  # not JSON-serializable
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("b", bad_body)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    original_content = rsps.calls[0].response.content
    assert resp.content == original_content
    assert "Warning" in capsys.readouterr().err


@rsps.activate
def test_call_api_response_filter_circular_ref_body_warns(
    capsys: pytest.CaptureFixture[str],
    no_request_filters: Any,
) -> None:
    """json.dumps が ValueError（循環参照等）を送出した場合も警告を出し元レスポンスを維持する。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    def circular_body(ctx: ResponseContext) -> ResponseContext:
        d: dict = {}
        d["self"] = d  # circular reference -> ValueError
        ctx.body = d
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("c", circular_body)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    original_content = rsps.calls[0].response.content
    assert resp.content == original_content
    assert "Warning" in capsys.readouterr().err


@rsps.activate
def test_call_api_response_filter_updates_content_type_charset(no_request_filters: Any) -> None:
    """ボディを書き換えた場合、Content-Type に charset=utf-8 が補完される。"""
    rsps.add(
        rsps.GET,
        f"{BASE_URL_RF}/store/inventory",
        json={"dogs": 1},
        status=200,
        headers={"Content-Type": "application/json"},
    )

    def add_key(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["cats"] = 99
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("a", add_key)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert "charset=utf-8" in resp.headers.get("Content-Type", "")
    assert resp.json() == {"dogs": 1, "cats": 99}


@rsps.activate
def test_call_api_response_filter_replaces_existing_charset(no_request_filters: Any) -> None:
    """既存の charset が utf-8 以外の場合、charset=utf-8 に置き換えられる。"""
    rsps.add(
        rsps.GET,
        f"{BASE_URL_RF}/store/inventory",
        json={"dogs": 1},
        status=200,
        headers={"Content-Type": "application/json; charset=iso-8859-1"},
    )

    def add_key(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["cats"] = 99
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("a", add_key)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    ct = resp.headers.get("Content-Type", "")
    assert "charset=utf-8" in ct
    assert "iso-8859-1" not in ct
    assert resp.json() == {"dogs": 1, "cats": 99}


@rsps.activate
def test_call_api_response_filter_updates_content_length(no_request_filters: Any) -> None:
    """ボディを書き換えた場合、Content-Length が新しいバイト長に更新される。"""
    rsps.add(rsps.GET, f"{BASE_URL_RF}/store/inventory", json={"dogs": 1}, status=200)

    def add_key(ctx: ResponseContext) -> ResponseContext:
        assert isinstance(ctx.body, dict)
        ctx.body["cats"] = 99
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("a", add_key)]):
        resp = call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    expected_len = len(resp.content)
    assert resp.headers.get("Content-Length") == str(expected_len)


@rsps.activate
def test_call_api_response_filter_case_insensitive_content_type(no_request_filters: Any) -> None:
    """Content-Type の大文字小文字を区別せず JSON としてパースする。"""
    rsps.add(
        rsps.GET,
        f"{BASE_URL_RF}/store/inventory",
        json={"dogs": 1},
        status=200,
        headers={"Content-Type": "Application/JSON"},
    )
    received: list[ResponseContext] = []

    def capture(ctx: ResponseContext) -> ResponseContext:
        received.append(ctx)
        return ctx

    with patch("papycli.request_filter.load_response_filters", return_value=[("c", capture)]):
        call_api("get", "/store/inventory", BASE_URL_RF, APIDEF_RF)

    assert received[0].body == {"dogs": 1}
