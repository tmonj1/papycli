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
    if schema_type and not _type_matches(value, schema_type):
        warnings.append(
            f"[response] {path or '/'}: "
            f"expected {schema_type}, got {_python_type_name(value)}"
        )
        return  # 型不一致の場合は以降のチェックをスキップ

    # enum チェック
    if "enum" in schema and value not in schema["enum"]:
        warnings.append(
            f"[response] {path or '/'}: "
            f"value {value!r} is not in enum {schema['enum']}"
        )

    # オブジェクト検証
    if schema_type == "object" and isinstance(value, dict):
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

    # 配列検証
    elif schema_type == "array" and isinstance(value, list):
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                _check_value(item, items_schema, f"{path}[{i}]", warnings)


def check_response(
    resp: requests.Response,
    raw_spec: dict[str, Any],
    method: str,
    template: str,
) -> list[str]:
    """レスポンスが OpenAPI スキーマ定義に合致しているかチェックする。

    Returns:
        警告メッセージのリスト（問題なければ空リスト）。
    """
    content_type = resp.headers.get("Content-Type", "").lower()
    if "application/json" not in content_type:
        return []

    try:
        body = resp.json()
    except ValueError:
        return ["[response] body: failed to parse JSON response"]

    paths = raw_spec.get("paths", {})
    path_item = paths.get(template, {})
    operation = path_item.get(method, {})
    responses = operation.get("responses", {})

    status_str = str(resp.status_code)
    response_def = responses.get(status_str) or responses.get("default")
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

    warnings: list[str] = []
    _check_value(body, schema, "", warnings)
    return warnings
