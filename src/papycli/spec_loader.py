"""OpenAPI spec の読み込み・$ref 解決・内部フォーマット変換."""

import copy
import json
from pathlib import Path
from typing import Any

import yaml


def load_spec(path: Path) -> dict[str, Any]:
    """JSON または YAML の OpenAPI spec ファイルを読み込む。"""
    with path.open(encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)  # type: ignore[no-any-return]
        return json.load(f)  # type: ignore[no-any-return]


def _decode_pointer_token(token: str) -> str:
    """JSON Pointer トークンのエスケープを解除する (~1 → /, ~0 → ~)。"""
    return token.replace("~1", "/").replace("~0", "~")


def _resolve_json_pointer(ref: str, root: dict[str, Any]) -> Any:
    """'#/a/b/c' 形式の JSON Pointer を解決する。"""
    if not ref.startswith("#/"):
        raise ValueError(f"Unsupported $ref: {ref!r} (only internal '#/...' refs are supported)")
    parts = ref[2:].split("/")
    node: Any = root
    for part in parts:
        part = _decode_pointer_token(part)
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"$ref target not found: {ref!r}")
        node = node[part]
    return node


def resolve_refs(
    obj: Any,
    root: dict[str, Any],
    _visited: frozenset[str] = frozenset(),
) -> Any:
    """オブジェクト中のすべての $ref を再帰的に解決する。循環参照は空 dict で打ち切る。"""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref: str = obj["$ref"]
            if ref in _visited:
                return {}  # 循環参照ガード
            target = _resolve_json_pointer(ref, root)
            return resolve_refs(copy.deepcopy(target), root, _visited | {ref})
        return {k: resolve_refs(v, root, _visited) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_refs(item, root, _visited) for item in obj]
    return obj


def _extract_schema_properties(
    schema: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    """スキーマから (required フィールド名リスト, properties dict) を取り出す。allOf に対応。"""
    required: list[str] = []
    properties: dict[str, Any] = {}

    for sub in schema.get("allOf", []):
        r, p = _extract_schema_properties(sub)
        required.extend(r)
        properties.update(p)

    required.extend(schema.get("required", []))
    properties.update(schema.get("properties", {}))
    return required, properties


def _param_entry(
    name: str, schema: dict[str, Any], required: bool, description: str = ""
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name,
        "type": schema.get("type", "string"),
        "required": required,
    }
    if "enum" in schema:
        entry["enum"] = schema["enum"]
    if description:
        entry["description"] = description
    return entry


def spec_to_apidef(spec: dict[str, Any]) -> dict[str, Any]:
    """解決済み OpenAPI spec を papycli 内部 API 定義フォーマットに変換する。"""
    apidef: dict[str, Any] = {}
    paths: dict[str, Any] = spec.get("paths", {})

    for path, path_item in paths.items():
        # path レベルの共通パラメータ
        common_params: dict[str, Any] = {
            p["name"]: p for p in path_item.get("parameters", [])
        }
        methods = []

        for method in ("get", "post", "put", "patch", "delete"):
            operation: dict[str, Any] | None = path_item.get(method)
            if operation is None:
                continue

            # path レベル + operation レベルをマージ (operation が優先)
            merged_params = {**common_params}
            for p in operation.get("parameters", []):
                merged_params[p["name"]] = p

            query_parameters = [
                _param_entry(
                    p["name"],
                    p.get("schema", {}),
                    bool(p.get("required", False)),
                    p.get("description", ""),
                )
                for p in merged_params.values()
                if p.get("in") == "query"
            ]

            # リクエストボディ (application/json のみ)
            post_parameters: list[dict[str, Any]] = []
            json_schema = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            if json_schema:
                req_fields, props = _extract_schema_properties(json_schema)
                post_parameters = [
                    _param_entry(
                        name, prop_schema, name in req_fields, prop_schema.get("description", "")
                    )
                    for name, prop_schema in props.items()
                ]

            op_description = operation.get("summary") or operation.get("description") or ""
            methods.append(
                {
                    "method": method,
                    "description": op_description,
                    "query_parameters": query_parameters,
                    "post_parameters": post_parameters,
                }
            )

        if methods:
            apidef[path] = methods

    return apidef


def collect_schema_refs(
    obj: Any,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """obj 内の $ref から参照される components/schemas エントリを推移的に収集する。

    Returns:
        参照されたスキーマ名をキー、スキーマ定義を値とする dict。
    """
    components = spec.get("components")
    schemas_raw = components.get("schemas") if isinstance(components, dict) else None
    schemas: dict[str, Any] = schemas_raw if isinstance(schemas_raw, dict) else {}
    result: dict[str, Any] = {}
    _visited: set[str] = set()        # 収集済みスキーマ名（循環ガード）
    _visited_refs: set[str] = set()   # 非スキーマ内部 ref の循環ガード

    def _collect(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if ref and isinstance(ref, str) and ref.startswith("#/"):
                parts = ref[2:].split("/")
                if len(parts) == 3 and parts[0] == "components" and parts[1] == "schemas":
                    # #/components/schemas/{SchemaName} への参照
                    name = _decode_pointer_token(parts[2])
                    if name not in _visited and name in schemas:
                        _visited.add(name)
                        result[name] = schemas[name]
                        _collect(schemas[name])
                elif ref not in _visited_refs:
                    # その他の内部 ref（parameters, pathItems 等）→ 解決して走査
                    _visited_refs.add(ref)
                    try:
                        _collect(_resolve_json_pointer(ref, spec))
                    except (ValueError, KeyError):
                        pass
            else:
                for v in node.values():
                    _collect(v)
        elif isinstance(node, list):
            for item in node:
                _collect(item)

    _collect(obj)
    return result


def extract_base_url(spec: dict[str, Any]) -> str:
    """spec から servers[0].url を返す。存在しない場合は空文字。"""
    servers = spec.get("servers", [])
    if servers:
        return str(servers[0].get("url", ""))
    return ""
