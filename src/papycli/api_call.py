"""HTTP リクエスト実行・パステンプレートマッチング・パラメータ構築."""

import json
import os
import re
from collections.abc import Sequence
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


def _set_or_append(obj: dict[str, Any], key: str, value: str) -> None:
    """dict にキーが既存なら配列に、なければ単値として設定する。"""
    if key not in obj:
        obj[key] = value
    elif isinstance(obj[key], list):
        obj[key].append(value)
    else:
        obj[key] = [obj[key], value]


def build_body(pairs: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """(-p name value) ペアから JSON ボディ dict を構築する。

    - 同じキーを繰り返すと JSON 配列になる
    - ドット記法 (category.id) で 1 レベルのネストオブジェクトになる
    """
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
            _set_or_append(result, name, value)
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
) -> requests.Response:
    """API を呼び出し、レスポンスを返す。"""
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
    if not any(op["method"] == method for op in ops):
        available = [op["method"] for op in ops]
        raise ValueError(
            f"Method '{method}' is not defined for '{template}'. "
            f"Available: {', '.join(available)}"
        )

    expanded = expand_path(template, path_params)
    url = base_url.rstrip("/") + expanded

    custom_env = os.environ.get("PAPYCLI_CUSTOM_HEADER")
    headers = parse_headers(extra_headers, custom_env)

    json_body: dict[str, Any] | None = None
    if raw_body is not None:
        json_body = json.loads(raw_body)
    elif body_params:
        json_body = build_body(body_params)

    return requests.request(
        method=method.upper(),
        url=url,
        params=list(query_params),
        json=json_body,
        headers=headers,
    )
