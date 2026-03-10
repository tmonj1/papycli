"""HTTP リクエスト実行・パステンプレートマッチング・パラメータ構築."""

import json
import os
import re
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# パステンプレートマッチング
# ---------------------------------------------------------------------------


def _template_to_regex(template: str) -> tuple[str, list[str]]:
    """/pet/{petId} → (r'/pet/([^/]+)', ['petId']) に変換する。"""
    param_names: list[str] = []
    parts = re.split(r"\{([^}]+)\}", template)
    pattern_parts: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            pattern_parts.append(re.escape(part))
        else:
            param_names.append(part)
            pattern_parts.append("([^/]+)")
    return "".join(pattern_parts), param_names


def match_path_template(
    resource: str, templates: list[str]
) -> tuple[str, dict[str, str]] | None:
    """resource をテンプレート一覧にマッチさせる。

    完全一致を優先し、次にテンプレート変数が少ない（具体的な）順。
    マッチしない場合は None を返す。
    """
    if resource in templates:
        return resource, {}

    matches: list[tuple[str, dict[str, str], int]] = []
    for template in templates:
        pattern, param_names = _template_to_regex(template)
        m = re.fullmatch(pattern, resource)
        if m:
            path_params = dict(zip(param_names, m.groups()))
            matches.append((template, path_params, len(param_names)))

    if not matches:
        return None

    matches.sort(key=lambda x: x[2])
    template, path_params, _ = matches[0]
    return template, path_params


def expand_path(template: str, path_params: dict[str, str]) -> str:
    """/pet/{petId} + {petId: '99'} → /pet/99"""
    result = template
    for name, value in path_params.items():
        result = result.replace(f"{{{name}}}", value)
    return result


# ---------------------------------------------------------------------------
# パラメータ構築
# ---------------------------------------------------------------------------


def _set_or_append(obj: dict[str, Any], key: str, value: Any) -> None:
    """dict にキーが既存なら配列に、なければ単値として設定する。"""
    if key not in obj:
        obj[key] = value
    elif isinstance(obj[key], list):
        obj[key].append(value)
    else:
        obj[key] = [obj[key], value]


def _coerce_value(value: str, type_str: str, name: str) -> Any:
    """API 定義の type に基づいて文字列値を適切な Python 型に変換する。

    変換に失敗した場合は警告を出力して文字列のまま返す。
    """
    try:
        if type_str == "integer":
            return int(value)
        if type_str == "number":
            return float(value)
        if type_str == "boolean":
            if value.lower() in ("true", "1"):
                return True
            if value.lower() in ("false", "0"):
                return False
            raise ValueError(f"not a boolean value: {value!r}")
    except (ValueError, TypeError) as e:
        print(
            f"Warning: cannot convert '{value}' to {type_str} for '{name}' ({e}),"
            " sending as string",
            file=sys.stderr,
        )
    return value


def build_body(
    pairs: Sequence[tuple[str, str]],
    post_parameters: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """(-p name value) ペアから JSON ボディ dict を構築する。

    - 同じキーを繰り返すと JSON 配列になる
    - ドット記法 (category.id) で 1 レベルのネストオブジェクトになる
    - post_parameters が渡された場合、type フィールドに基づき値を適切な型に変換する
    """
    type_map: dict[str, str] = (
        {p["name"]: p.get("type", "string") for p in post_parameters}
        if post_parameters
        else {}
    )

    result: dict[str, Any] = {}
    for name, value in pairs:
        if "." in name:
            parent, child = name.split(".", 1)
            if parent not in result:
                result[parent] = {}
            parent_obj = result[parent]
            if not isinstance(parent_obj, dict):
                raise ValueError(
                    f"Cannot use dot notation on '{parent}': already a scalar or array"
                )
            _set_or_append(parent_obj, child, value)
        else:
            type_str = type_map.get(name, "string")
            coerced = _coerce_value(value, type_str, name)
            _set_or_append(result, name, coerced)
    return result


# ---------------------------------------------------------------------------
# ヘッダー解析
# ---------------------------------------------------------------------------


def parse_headers(
    header_strings: Sequence[str],
    custom_header_env: str | None = None,
) -> dict[str, str]:
    """"-H Header: Value" 文字列と PAPYCLI_CUSTOM_HEADER 環境変数からヘッダー dict を構築する。

    環境変数より -H オプションが優先される。
    """
    headers: dict[str, str] = {}

    if custom_header_env:
        for line in custom_header_env.splitlines():
            line = line.strip()
            if line and ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip()] = v.strip()

    for h in header_strings:
        if ":" not in h:
            raise ValueError(f"Invalid header format: {h!r} (expected 'Name: Value')")
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()

    return headers


# ---------------------------------------------------------------------------
# ログ書き込み
# ---------------------------------------------------------------------------

_SENSITIVE_HEADERS = frozenset({
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
})


def _write_log(
    logfile: str,
    method: str,
    url: str,
    query_params: list[tuple[str, str]],
    body: Any,
    headers: dict[str, str],
    resp: requests.Response,
) -> None:
    """リクエスト・レスポンスの情報を logfile に追記する。"""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # クエリパラメータ: 同一キーは list にまとめて表示（_set_or_append を再利用）
    q_dict: dict[str, Any] = {}
    for k, v in query_params:
        _set_or_append(q_dict, k, v)
    q_str = json.dumps(q_dict, ensure_ascii=False) if q_dict else "(none)"

    body_str = json.dumps(body, ensure_ascii=False) if body is not None else "(none)"
    masked = {
        k: "***" if k.lower() in _SENSITIVE_HEADERS else v for k, v in headers.items()
    }
    headers_str = json.dumps(masked, ensure_ascii=False) if masked else "(none)"

    try:
        resp_body = resp.json()
        resp_str = json.dumps(resp_body, ensure_ascii=False)
    except ValueError:
        resp_str = resp.text or "(empty)"

    entry = (
        f"[{timestamp}] {method.upper()} {url}\n"
        f"  Query: {q_str}\n"
        f"  Body: {body_str}\n"
        f"  Headers: {headers_str}\n"
        f"  Status: {resp.status_code}\n"
        f"  Response: {resp_str}\n"
    )

    try:
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        with Path(logfile).open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"Warning: failed to write log to '{logfile}': {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# HTTP 実行
# ---------------------------------------------------------------------------


def call_api(
    method: str,
    resource: str,
    base_url: str,
    apidef: dict[str, Any],
    *,
    query_params: Sequence[tuple[str, str]] = (),
    body_params: Sequence[tuple[str, str]] = (),
    raw_body: str | None = None,
    extra_headers: Sequence[str] = (),
    logfile: str | None = None,
) -> requests.Response:
    """API を呼び出し、レスポンスを返す。"""
    from papycli.request_filter import RequestContext, apply_filters, load_filters

    if not base_url:
        raise RuntimeError(
            "Base URL is not configured. Edit papycli.conf and set the 'url' field."
        )

    templates = list(apidef.keys())
    match = match_path_template(resource, templates)
    if match is None:
        raise ValueError(
            f"No matching path for '{resource}'.\n"
            f"Available paths: {', '.join(templates)}"
        )
    template, path_params = match

    ops: list[dict[str, Any]] = apidef[template]
    op = next((o for o in ops if o["method"] == method), None)
    if op is None:
        available = [o["method"] for o in ops]
        raise ValueError(
            f"Method '{method}' is not defined for '{template}'. "
            f"Available: {', '.join(available)}"
        )

    expanded = expand_path(template, path_params)
    url = base_url.rstrip("/") + expanded

    custom_env = os.environ.get("PAPYCLI_CUSTOM_HEADER")
    headers = parse_headers(extra_headers, custom_env)

    json_body: dict[str, Any] | list[Any] | str | int | float | bool | None = None
    if raw_body is not None:
        json_body = json.loads(raw_body)
    elif body_params:
        json_body = build_body(body_params, op.get("post_parameters"))

    ctx = RequestContext(
        method=method,
        url=url,
        query_params=list(query_params),
        body=json_body,
        headers=headers,
    )
    ctx = apply_filters(ctx, load_filters())

    # method はフィルターから変更不可のため、API 定義マッチング時に確定した元の値を使う。
    resp = requests.request(
        method=method.upper(),
        url=ctx.url,
        params=ctx.query_params,
        json=ctx.body,
        headers=ctx.headers,
    )

    if logfile:
        # ログにはフィルター適用前のユーザー指定ヘッダー（headers）を使う。
        # ctx.headers にはフィルタープラグインが追加したヘッダーが含まれる可能性があり、
        # 機密情報が漏洩するリスクがあるため記録しない。
        _write_log(logfile, method, ctx.url, ctx.query_params, ctx.body, headers, resp)

    return resp
