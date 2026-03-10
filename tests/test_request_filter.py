"""request_filter モジュールのテスト."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import responses as rsps

from papycli.api_call import call_api
from papycli.request_filter import RequestContext, apply_filters, load_filters

# ---------------------------------------------------------------------------
# RequestContext
# ---------------------------------------------------------------------------


def test_request_context_defaults() -> None:
    ctx = RequestContext(method="get", url="http://example.com/api")
    assert ctx.query_params == {}
    assert ctx.body is None
    assert ctx.headers == {}


def test_request_context_fields() -> None:
    ctx = RequestContext(
        method="post",
        url="http://example.com/pet",
        query_params={"status": ["available"]},
        body={"name": "Dog"},
        headers={"Authorization": "Bearer token"},
    )
    assert ctx.method == "post"
    assert ctx.url == "http://example.com/pet"
    assert ctx.query_params == {"status": ["available"]}
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
    ctx.query_params.setdefault("injected", []).append("value")
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
    ctx = RequestContext(method="get", url="http://example.com/", query_params={"a": ["1"]})
    result = apply_filters(ctx, [("q-filter", _add_query_filter)])
    assert result.query_params["injected"] == ["value"]
    assert result.query_params["a"] == ["1"]


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
        ctx.query_params.setdefault("token", []).append("abc")
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
