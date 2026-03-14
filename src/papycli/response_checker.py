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

    # enum チェック（null 値も対象: type が null/null 含む union で enum に含まれない場合も警告）
    # schema["enum"] が list でない場合はスキップする（不正なスキーマでのクラッシュを防ぐ）
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        warnings.append(
            f"[response] {path or '/'}: "
            f"value {value!r} is not in enum {enum_values}"
        )

    # null 値のチェック:
    # type が省略されていて object/array キーワードがある場合は null を型違反として警告する。
    # type == "null" またはリストに "null" が含まれる場合は上の型チェックで通過済みのため、
    # ここに到達するのは schema_type が None のケースのみ。
    if value is None:
        _object_kws = ("properties", "required", "additionalProperties")
        if schema_type is None and any(k in schema for k in _object_kws):
            warnings.append(
                f"[response] {path or '/'}: expected object, got null"
            )
        elif schema_type is None and "items" in schema:
            warnings.append(
                f"[response] {path or '/'}: expected array, got null"
            )
        return

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
        properties_raw = schema.get("properties", {})
        properties: dict[str, Any] = properties_raw if isinstance(properties_raw, dict) else {}
        required_raw = schema.get("required", [])
        required: list[str] = required_raw if isinstance(required_raw, list) else []

        for req_field in required:
            if req_field not in value:
                warnings.append(
                    f"[response] {path or '/'}: required field '{req_field}' is missing"
                )

        for prop_name, prop_schema in properties.items():
            if prop_name in value and isinstance(prop_schema, dict):
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

    spec にオペレーションとレスポンスマップが存在する場合、ステータスコードを照合する。
    ボディスキーマ検証は JSON コンテンツタイプのレスポンスのみを対象とする。

    Args:
        _body: 事前にパース済みのレスポンスボディ。省略時は resp.json() でパースする。

    Returns:
        警告メッセージのリスト（問題なければ空リスト）。
    """
    warnings: list[str] = []

    # ステータスコード照合（コンテンツタイプに関わらず常に実施する）
    # $ref 解決中の KeyError/ValueError をキャッチし、API 呼び出しを中断させない。
    try:
        paths_raw = raw_spec.get("paths", {})
        paths: dict[str, Any] = paths_raw if isinstance(paths_raw, dict) else {}
        # Path Item が $ref の場合も正しく解決する
        path_item = resolve_refs(paths.get(template, {}), raw_spec)
        if not isinstance(path_item, dict):
            return []
        operation = path_item.get(method, {})
        if not isinstance(operation, dict):
            return []
        responses = operation.get("responses", {})
        if not isinstance(responses, dict):
            return []

        # YAML で読み込んだ場合にステータスコードキーが整数になることがあるため文字列に正規化する
        responses_str: dict[str, Any] = {str(k): v for k, v in responses.items()}

        # ステータスコードを完全一致 → 範囲指定（2XX/2xx 両方）→ default の順で探索する
        # 空 dict の場合の誤スルーを防ぐため or チェーンではなく in で判定する
        status_str = str(resp.status_code)
        range_upper = f"{resp.status_code // 100}XX"
        range_lower = f"{resp.status_code // 100}xx"
        if status_str in responses_str:
            response_def: Any = responses_str[status_str]
        elif range_upper in responses_str:
            response_def = responses_str[range_upper]
        elif range_lower in responses_str:
            response_def = responses_str[range_lower]
        elif "default" in responses_str:
            response_def = responses_str["default"]
        else:
            response_def = None

        # spec に定義されていないステータスコードの場合は警告して終了
        if response_def is None:
            defined = ", ".join(sorted(responses_str.keys()))
            warnings.append(
                f"[response] status: {resp.status_code} is not defined in the spec"
                + (f" (defined: {defined})" if defined else "")
            )
            return warnings
    except (KeyError, ValueError) as e:
        return [f"[response] spec: failed to resolve $ref: {e}"]

    # ボディスキーマ検証（JSON コンテンツタイプのレスポンスのみ対象）
    content_type = resp.headers.get("Content-Type", "").lower()
    # charset 等のパラメータを除いたベース型を抽出する
    base_content_type = content_type.split(";")[0].strip()
    # application/json および +json サフィックスを持つ JSON 互換メディアタイプ以外はスキップ
    if base_content_type != "application/json" and not base_content_type.endswith("+json"):
        return warnings

    # スキーマが存在する場合のみボディをパースする（スキーマ未定義のステータスでの
    # 誤警告を防ぐため、先にスキーマを確認する）。
    try:
        resolved_def = resolve_refs(response_def, raw_spec)
        if not isinstance(resolved_def, dict):
            return warnings
        content_map_raw: Any = resolved_def.get("content", {})
        content_map: dict[str, Any] = content_map_raw if isinstance(content_map_raw, dict) else {}
        # スキーマ探索: 完全一致 → application/json → +json サフィックスを持つ型の順
        schema: Any = None
        for key in [base_content_type, "application/json"] + [
            k for k in content_map if k.endswith("+json") and k != base_content_type
        ]:
            entry = content_map.get(key)
            if not isinstance(entry, dict):
                continue
            s = entry.get("schema")
            if isinstance(s, dict):
                schema = s
                break
        if not isinstance(schema, dict):
            return warnings
    except (KeyError, ValueError) as e:
        return warnings + [f"[response] schema: failed to resolve $ref: {e}"]

    if _body is _UNSET:
        try:
            body = resp.json()
        except ValueError:
            return warnings + ["[response] body: failed to parse JSON response"]
    else:
        body = _body

    _check_value(body, schema, "", warnings)
    return warnings
