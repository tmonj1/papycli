"""リクエスト前のパラメータ検証ロジック。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any


def _check_value(param: dict[str, Any], raw_value: Any) -> list[str]:
    """単一パラメータ値に対して型・enum チェックを行い、警告メッセージのリストを返す。

    raw_value は文字列（-p/-q 経由）または JSON から解析された任意の値。
    """
    warnings: list[str] = []
    name = param["name"]
    ptype = param.get("type", "")
    enum = param.get("enum")

    if ptype == "integer":
        try:
            int(str(raw_value))
        except ValueError:
            warnings.append(
                f"Warning: parameter '{name}' expects integer, got '{raw_value}'"
            )
    elif ptype == "boolean":
        if str(raw_value).lower() not in {"true", "false", "1", "0"}:
            warnings.append(
                f"Warning: parameter '{name}' expects boolean (true/false), got '{raw_value}'"
            )

    if enum is not None and str(raw_value) not in [str(e) for e in enum]:
        warnings.append(
            f"Warning: parameter '{name}' value '{raw_value}' is not in enum {enum}"
        )

    return warnings


def check_request(
    apidef: dict[str, Any],
    method: str,
    resource: str,
    query_params: Sequence[tuple[str, str]],
    body_params: Sequence[tuple[str, str]],
    raw_body: str | None,
) -> list[str]:
    """リクエスト前に必須パラメータ・型・enum を検証し、警告メッセージのリストを返す。

    問題がなければ空リストを返す。
    """
    from papycli.api_call import match_path_template

    warnings: list[str] = []

    match = match_path_template(resource, list(apidef.keys()))
    if match is None:
        return warnings  # パス不明は api_call 側でエラーになるのでここでは無視

    template, _ = match
    ops: list[dict[str, Any]] = apidef[template]
    op = next((o for o in ops if o["method"] == method), None)
    if op is None:
        return warnings

    # ---- クエリパラメータのチェック ----
    q_params: list[dict[str, Any]] = op.get("query_parameters", [])
    provided_query = {name for name, _ in query_params}

    for p in q_params:
        if p.get("required") and p["name"] not in provided_query:
            warnings.append(f"Warning: required query parameter '{p['name']}' is missing")

    for name, value in query_params:
        param_def = next((p for p in q_params if p["name"] == name), None)
        if param_def:
            warnings.extend(_check_value(param_def, value))

    # ---- ボディパラメータのチェック ----
    b_params: list[dict[str, Any]] = op.get("post_parameters", [])

    if raw_body is not None:
        # -d JSON の場合: JSON をパースして各フィールドをチェック
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError:
            warnings.append("Warning: --check: failed to parse raw body as JSON")
            parsed = {}

        if not isinstance(parsed, dict):
            warnings.append(
                "Warning: --check: raw body is not a JSON object; parameter checks skipped"
            )
            parsed = {}

        body_dict: dict[str, Any] = parsed
        provided_body = set(body_dict.keys())
        for p in b_params:
            if p.get("required") and p["name"] not in provided_body:
                warnings.append(f"Warning: required body parameter '{p['name']}' is missing")

        for p in b_params:
            if p["name"] in body_dict:
                warnings.extend(_check_value(p, body_dict[p["name"]]))
    else:
        # -p ペアの場合
        provided_body = {name for name, _ in body_params}

        for p in b_params:
            if p.get("required") and p["name"] not in provided_body:
                warnings.append(f"Warning: required body parameter '{p['name']}' is missing")

        for name, value in body_params:
            param_def = next((p for p in b_params if p["name"] == name), None)
            if param_def:
                warnings.extend(_check_value(param_def, value))

    return warnings
