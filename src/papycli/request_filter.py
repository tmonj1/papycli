"""リクエストフィルタープラグイン機構.

エントリポイントグループ ``papycli.request_filters`` に登録されたフィルター関数を
プラグイン名の昇順で呼び出し、リクエスト前に URL・クエリパラメータ・ボディ・ヘッダーを
変換できるようにする。

プラグイン側の ``pyproject.toml`` 設定例::

    [project.entry-points."papycli.request_filters"]
    my-filter = "my_plugin:request_filter"

フィルター関数のシグネチャ::

    def request_filter(context: RequestContext) -> RequestContext: ...
"""

from __future__ import annotations

import importlib.metadata
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

ENTRY_POINT_GROUP = "papycli.request_filters"

FilterFunc = Callable[["RequestContext"], "RequestContext"]


@dataclass
class RequestContext:
    """フィルターに渡されるリクエストコンテキスト."""

    method: str
    """HTTP メソッド（"get", "post" 等、小文字）."""

    url: str
    """完全 URL（パスパラメータ展開済み）."""

    query_params: dict[str, list[str]] = field(default_factory=dict)
    """クエリパラメータ（同一キーの複数値はリストで保持）."""

    body: dict[str, Any] | list[Any] | None = None
    """JSON ボディ（-d 指定時は dict/list、未指定時は None）."""

    headers: dict[str, str] = field(default_factory=dict)
    """カスタム HTTP ヘッダー."""


def load_filters() -> list[tuple[str, FilterFunc]]:
    """``papycli.request_filters`` グループのプラグインをプラグイン名の昇順でロードする。

    ロードに失敗したプラグインは警告を出力してスキップする。
    """
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    result: list[tuple[str, FilterFunc]] = []
    for ep in sorted(eps, key=lambda e: e.name):
        try:
            func: FilterFunc = ep.load()
            result.append((ep.name, func))
        except Exception as e:
            print(
                f"Warning: failed to load request filter '{ep.name}': {e}",
                file=sys.stderr,
            )
    return result


def apply_filters(
    ctx: RequestContext,
    filters: list[tuple[str, FilterFunc]],
) -> RequestContext:
    """フィルターを順番に適用する。

    例外を送出したフィルターは警告を出力してスキップし、残りのフィルターの処理は継続する。
    """
    for name, func in filters:
        try:
            ctx = func(ctx)
        except Exception as e:
            print(
                f"Warning: request filter '{name}' raised an exception: {e}",
                file=sys.stderr,
            )
    return ctx
