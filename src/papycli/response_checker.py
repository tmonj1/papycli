"""レスポンスの OpenAPI スキーマ適合チェック."""

from typing import Any

import requests

from papycli.spec_loader import resolve_refs


def _python_type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _type_matches(value: Any, schema_type: str) -> bool:
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "null":
        return value is None
    return True  # 未知の型はスキップ


def _check_value(
    value: Any,
    schema: dict[str, Any],
    path: str,
    warnings: list[str],
) -> None:
    """value が schema に適合しているか再帰的にチェックする。"""
    schema_type = schema.get("type")

    # 型チェック
    # schema_type が文字列の場合は単一型チェック、リストの場合はいずれかの型に一致するかチェック。
    # schema_type が None（省略）の場合は型チェックをスキップする。
    if isinstance(schema_type, str):
        if not _type_matches(value, schema_type):
            warnings.append(
                f"[response] {path or '/'}: "
                f"expected {schema_type}, got {_python_type_name(value)}"
            )
            return  # 型不一致の場合は以降のチェックをスキップ
    elif isinstance(schema_type, list):
        if not any(_type_matches(value, t) for t in schema_type):
            warnings.append(
                f"[response] {path or '/'}: "
                f"expected one of {schema_type}, got {_python_type_name(value)}"
            )
            return

    # null 値はこれ以上チェックしない
    if value is None:
        return

    # enum チェック
    if "enum" in schema and value not in schema["enum"]:
        warnings.append(
            f"[response] {path or '/'}: "
            f"value {value!r} is not in enum {schema['enum']}"
        )

    # オブジェクト検証:
    # type == "object"、union 型リストに "object" が含まれる、または
    # type が省略されていてもオブジェクトキーワードがある場合に検証する。
    _object_keywords = ("properties", "required", "additionalProperties")
    is_object_schema = (
        schema_type == "object"
        or (isinstance(schema_type, list) and "object" in schema_type)
        or (schema_type is None and any(k in schema for k in _object_keywords))
    )
    if is_object_schema and isinstance(value, dict):
        properties: dict[str, Any] = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        for req_field in required:
            if req_field not in value:
                warnings.append(
                    f"[response] {path or '/'}: required field '{req_field}' is missing"
                )

        for prop_name, prop_schema in properties.items():
            if prop_name in value:
                _check_value(
                    value[prop_name],
                    prop_schema,
                    f"{path}/{prop_name}",
                    warnings,
                )

        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    warnings.append(
                        f"[response] {path or '/'}: unexpected field '{key}'"
                    )
    elif is_object_schema and schema_type is None:
        # type が省略されているが object キーワードから object スキーマと判断した場合、
        # value が dict でなければ型違反として警告する。
        warnings.append(
            f"[response] {path or '/'}: expected object, got {_python_type_name(value)}"
        )

    # 配列検証:
    # type == "array"、union 型リストに "array" が含まれる、または
    # type が省略されていても items がある場合に検証する。
    is_array_schema = (
        schema_type == "array"
        or (isinstance(schema_type, list) and "array" in schema_type)
        or (schema_type is None and "items" in schema)
    )
    if is_array_schema and isinstance(value, list):
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                # ルートレベル（path が空）の配列アイテムも "/" から始まるパスにする
                item_path = f"{path}[{i}]" if path else f"/[{i}]"
                _check_value(item, items_schema, item_path, warnings)
    elif is_array_schema and schema_type is None:
        # type が省略されているが items から array スキーマと判断した場合、
        # value が list でなければ型違反として警告する。
        warnings.append(
            f"[response] {path or '/'}: expected array, got {_python_type_name(value)}"
        )


_UNSET = object()


def check_response(
    resp: requests.Response,
    raw_spec: dict[str, Any],
    method: str,
    template: str,
    *,
    _body: Any = _UNSET,
) -> list[str]:
    """レスポンスが OpenAPI スキーマ定義に合致しているかチェックする。

    Args:
        _body: 事前にパース済みのレスポンスボディ。省略時は resp.json() でパースする。

    Returns:
        警告メッセージのリスト（問題なければ空リスト）。
    """
    content_type = resp.headers.get("Content-Type", "").lower()
    if "application/json" not in content_type:
        return []

    # スキーマが存在する場合のみボディをパースする（空ボディや定義なしのステータスでの
    # 誤警告を防ぐため、先にレスポンス定義とスキーマを確認する）。
    paths = raw_spec.get("paths", {})
    path_item = paths.get(template, {})
    operation = path_item.get(method, {})
    responses = operation.get("responses", {})

    # ステータスコードを完全一致 → 範囲指定（例: 2XX）→ default の順で探索する
    status_str = str(resp.status_code)
    range_str = f"{resp.status_code // 100}XX"
    response_def = (
        responses.get(status_str)
        or responses.get(range_str)
        or responses.get("default")
    )
    if response_def is None:
        return []

    resolved_def = resolve_refs(response_def, raw_spec)
    schema = (
        resolved_def.get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    if not isinstance(schema, dict):
        return []

    if _body is _UNSET:
        try:
            body = resp.json()
        except ValueError:
            return ["[response] body: failed to parse JSON response"]
    else:
        body = _body

    warnings: list[str] = []
    _check_value(body, schema, "", warnings)
    return warnings
