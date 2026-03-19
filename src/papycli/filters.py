"""リクエスト・レスポンスフィルタープラグイン機構.

エントリポイントグループ ``papycli.request_filters`` に登録されたフィルター関数を
プラグイン名の昇順で呼び出し、リクエスト前に URL・クエリパラメータ・ボディ・ヘッダーを
変換できるようにする。

同様に ``papycli.response_filters`` グループのフィルター関数を呼び出し、
レスポンス受信後にステータスコード・理由フレーズ（reason）・ボディ・ヘッダーを参照・変更できるようにする。

プラグイン側の ``pyproject.toml`` 設定例::

    [project.entry-points."papycli.request_filters"]
    my-filter = "my_plugin:request_filter"

    [project.entry-points."papycli.response_filters"]
    my-filter = "my_plugin:response_filter"

フィルター関数のシグネチャ::

    def request_filter(context: RequestContext) -> RequestContext: ...
    def response_filter(context: ResponseContext) -> ResponseContext | None: ...
"""

from __future__ import annotations

import copy
import importlib.metadata
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, TypeAlias

REQUEST_ENTRY_POINT_GROUP = "papycli.request_filters"
RESPONSE_ENTRY_POINT_GROUP = "papycli.response_filters"

JsonValue: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None
"""JSON 値を表す型エイリアス."""

FilterFunc = Callable[["RequestContext"], "RequestContext"]
ResponseFilterFunc = Callable[["ResponseContext"], "ResponseContext | None"]


@dataclass
class RequestContext:
    """フィルターに渡されるリクエストコンテキスト."""

    method: str
    """HTTP メソッド（"get", "post" 等、小文字）.

    .. note::
        フィルターはこのフィールドを変更してはならない。
        ``call_api()`` は API 定義のマッチングをリクエスト送信前に確定するため、
        フィルターがメソッドを変更しても送信メソッドには反映されない。
    """

    url: str
    """完全 URL（パスパラメータ展開済み）."""

    query_params: list[tuple[str, str]] = field(default_factory=list)
    """クエリパラメータ（順序保持。同一キーを繰り返す場合は同名タプルを複数追加する）.

    ``requests.request(params=...)`` と同じ形式で保持するため、キー間の順序は
    元の ``-q`` オプション指定順のまま維持される。
    """

    body: JsonValue = None
    """JSON ボディ（-d 指定時は任意の JSON 値（オブジェクト・配列・スカラ）、未指定時は None）."""

    headers: dict[str, str] = field(default_factory=dict)
    """カスタム HTTP ヘッダー."""

    spec: dict[str, Any] | None = field(default=None)
    """呼び出し中のオペレーション仕様（apidef 内の該当エントリ）.

    API 定義にマッチしたオペレーション dict を格納する。例::

        {
            "method": "get",
            "query_parameters": [{"name": "status", "type": "string", ...}],
            "post_parameters": [],
        }

    API 定義が解決できない場合（直接 ``RequestContext`` を構築するテスト等）は ``None``。

    .. note::
        フィルターはこのフィールドを変更してはならない。
        ``spec`` は API 定義から導出されたメタデータであり、フィルターが変更しても
        パラメータ検証や補完には反映されない。
    """


def load_filters() -> list[tuple[str, FilterFunc]]:
    """``papycli.request_filters`` グループのプラグインをプラグイン名の昇順でロードする。

    ロードに失敗したプラグインは警告を出力してスキップする。
    """
    eps = importlib.metadata.entry_points(group=REQUEST_ENTRY_POINT_GROUP)
    result: list[tuple[str, FilterFunc]] = []
    for ep in sorted(eps, key=lambda e: e.name):
        try:
            func: FilterFunc = ep.load()
        except Exception as e:
            print(
                f"Warning: failed to load request filter '{ep.name}': {e}",
                file=sys.stderr,
            )
            continue
        if not callable(func):
            print(
                f"Warning: entry point '{ep.name}' for group"
                f" '{REQUEST_ENTRY_POINT_GROUP}' is not callable and will be ignored.",
                file=sys.stderr,
            )
            continue
        result.append((ep.name, func))
    return result


def apply_filters(
    ctx: RequestContext,
    filters: list[tuple[str, FilterFunc]],
) -> RequestContext:
    """フィルターを順番に適用する。

    各フィルターは呼び出し前の ``ctx`` のスナップショットを受け取る。
    スナップショットは ``body`` を ``copy.deepcopy``、それ以外（``method``、
    ``url``、``query_params``、``headers``）は新しいコンテナへのシャローコピーで
    作成される（``query_params`` の要素 ``tuple`` と ``headers`` の値 ``str`` は
    immutable なためシャローコピーで十分）。

    ``spec`` は read-only フィールドのため、フィルターが変更しても後続フィルターや
    呼び出し元には反映されない。``apply_response_filters`` の ``request_body`` と同様に、
    フィルター適用前に ``original_spec`` を deepcopy で保存し、各フィルター成功後および
    全フィルター完了後に ``ctx.spec`` を元の値に復元することで、フィルターによる
    変更・インプレース変異・例外送出のいずれの場合も spec が汚染されないことを保証する。

    例外を送出したフィルター、および ``RequestContext`` 以外を返したフィルターは
    警告を出力して前の ``ctx`` を維持し、残りのフィルターの処理は継続する。
    これにより、フィルターが失敗する前にコンテキストをインプレース変更していても
    変更がキャンセルされ、後続フィルターへの影響を防ぐ。
    """
    if not filters:
        return ctx

    # spec は参照専用フィールドのため、フィルターによる変更を無視して元の値を保持する。
    # deepcopy することで後からの変更が original_spec に波及しないようにする。
    original_spec = copy.deepcopy(ctx.spec)
    for name, func in filters:
        # method と url は immutable な str なのでコピー不要。
        # query_params の要素（tuple）も immutable なのでリストのシャローコピーで十分。
        # headers の値は str なのでシャローコピーで十分。
        # body は dict / list の可能性があるため deepcopy する。
        # spec は original_spec の deepcopy を渡すことでフィルターが original_spec を
        # 変異させるリスクを排除する。
        snapshot = RequestContext(
            method=ctx.method,
            url=ctx.url,
            query_params=list(ctx.query_params),
            body=copy.deepcopy(ctx.body),
            headers=dict(ctx.headers),
            spec=copy.deepcopy(ctx.spec),
        )
        try:
            result = func(snapshot)
        except Exception as e:
            print(
                f"Warning: request filter '{name}' raised an exception: {e}",
                file=sys.stderr,
            )
            continue
        if not isinstance(result, RequestContext):
            print(
                f"Warning: request filter '{name}' returned {type(result).__name__!r}"
                " instead of RequestContext; skipping",
                file=sys.stderr,
            )
            continue
        # 後続フィルターへのスナップショットにも元の値が渡るよう、成功時にも復元する。
        result.spec = original_spec
        ctx = result
    # 全フィルターが失敗した場合も含め、常に元の spec で上書きする。
    ctx.spec = original_spec
    return ctx


# ---------------------------------------------------------------------------
# レスポンスフィルター
# ---------------------------------------------------------------------------


@dataclass
class ResponseContext:
    """レスポンスフィルターに渡されるコンテキスト."""

    method: str
    """リクエストに使用した HTTP メソッド（小文字）."""

    url: str
    """リクエストに使用した完全 URL."""

    status_code: int
    """HTTP レスポンスステータスコード."""

    reason: str
    """HTTP レスポンスの理由フレーズ（例: "OK", "Not Found"）."""

    headers: dict[str, str] = field(default_factory=dict)
    """レスポンスヘッダー."""

    body: JsonValue = None
    """パース済みレスポンスボディ.

    Content-Type が application/json のレスポンスは JSON としてパースされた値、
    それ以外はテキスト文字列（空の場合は None）が格納される。
    フィルターはこのフィールドを変更することでレスポンスボディを差し替えられる。
    """

    request_body: JsonValue = None
    """リクエストフィルター適用後の送信済みリクエストボディ（参照専用）.

    リクエストフィルターによって変換された後、実際にサーバーへ送信された JSON ボディ。
    ボディなしのリクエスト（GET 等）の場合は None。
    """


def load_response_filters() -> list[tuple[str, ResponseFilterFunc]]:
    """``papycli.response_filters`` グループのプラグインをプラグイン名の昇順でロードする。

    ロードに失敗したプラグインは警告を出力してスキップする。
    """
    eps = importlib.metadata.entry_points(group=RESPONSE_ENTRY_POINT_GROUP)
    result: list[tuple[str, ResponseFilterFunc]] = []
    for ep in sorted(eps, key=lambda e: e.name):
        try:
            func: ResponseFilterFunc = ep.load()
        except Exception as e:
            print(
                f"Warning: failed to load response filter '{ep.name}': {e}",
                file=sys.stderr,
            )
            continue
        if not callable(func):
            print(
                f"Warning: entry point '{ep.name}' for group"
                f" '{RESPONSE_ENTRY_POINT_GROUP}' is not callable and will be ignored.",
                file=sys.stderr,
            )
            continue
        result.append((ep.name, func))
    return result


def apply_response_filters(
    ctx: ResponseContext,
    filters: list[tuple[str, ResponseFilterFunc]],
) -> ResponseContext | None:
    """レスポンスフィルターを順番に適用する。

    各フィルターは呼び出し前の ``ctx`` のスナップショットを受け取る。
    ``body`` と ``request_body`` は ``copy.deepcopy``、それ以外はシャローコピーで作成される。

    フィルターが ``None`` を返した場合はチェーンを中断し、``None`` を返す。
    呼び出し元はこの戻り値を「レスポンスの出力を抑制する」シグナルとして扱う。

    例外を送出したフィルター、および ``ResponseContext`` でも ``None`` でもない値を返した
    フィルターは警告を出力して前の ``ctx`` を維持し、残りのフィルターの処理は継続する。
    """
    if not filters:
        return ctx

    # request_body は参照専用フィールドのため、フィルターによる変更を無視して元の値を保持する。
    # deepcopy することで呼び出し元が後から同じ dict/list を変更しても返り値が変化しないようにする。
    original_request_body = copy.deepcopy(ctx.request_body)
    for name, func in filters:
        snapshot = ResponseContext(
            method=ctx.method,
            url=ctx.url,
            status_code=ctx.status_code,
            reason=ctx.reason,
            headers=dict(ctx.headers),
            body=copy.deepcopy(ctx.body),
            request_body=copy.deepcopy(ctx.request_body),
        )
        try:
            result = func(snapshot)
        except Exception as e:
            print(
                f"Warning: response filter '{name}' raised an exception: {e}",
                file=sys.stderr,
            )
            continue
        if result is None:
            # None はレスポンス出力を抑制するシグナル。チェーンを即座に中断する。
            return None
        if not isinstance(result, ResponseContext):
            print(
                f"Warning: response filter '{name}' returned {type(result).__name__!r}"
                " instead of ResponseContext; skipping",
                file=sys.stderr,
            )
            continue
        # 後続フィルターへのスナップショットにも元の値が渡るよう、成功時にも復元する。
        result.request_body = original_request_body
        ctx = result
    # 全フィルターが失敗した場合も含め、常に deepcopy 済みの値で上書きする。
    ctx.request_body = original_request_body
    return ctx
