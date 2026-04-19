"""--summary / --summary-csv の出力処理。"""

import csv
import io
from typing import Any, TextIO

from rich.console import Console


def _format_param(p: dict[str, Any], flag: str) -> str:
    """パラメータを表示用文字列に変換する。

    例: -q status*[available|pending|sold]  / -p photoUrls*[]
    """
    name = p["name"]
    annotation = ""
    if p.get("required"):
        annotation += "*"
    if p.get("type") == "array":
        annotation += "[]"
    result = f"{flag} {name}{annotation}"
    if "enum" in p:
        enum_str = "|".join(str(e) for e in p["enum"])
        result += f"[{enum_str}]"
    return result


def build_rows(
    apidef: dict[str, Any],
    resource_filter: str | None = None,
) -> list[tuple[str, str, str]]:
    """(METHOD, path, params_str) のリストを返す。テストや CSV 生成にも利用。"""
    rows: list[tuple[str, str, str]] = []
    for path in sorted(apidef.keys()):
        if resource_filter and not path.startswith(resource_filter):
            continue
        for op in apidef[path]:
            q_parts = [_format_param(p, "-q") for p in op.get("query_parameters", [])]
            p_parts = [_format_param(p, "-p") for p in op.get("post_parameters", [])]
            params_str = "  ".join(q_parts + p_parts)
            rows.append((op["method"].upper(), path, params_str))
    return rows


def print_summary(
    apidef: dict[str, Any],
    resource_filter: str | None = None,
    *,
    file: TextIO | None = None,
) -> None:
    """エンドポイント一覧をリソース・メソッド別の構造化テキストで出力する。"""
    console = Console(file=file, highlight=False, no_color=(file is not None))
    found = False

    for path in sorted(apidef.keys()):
        if resource_filter and not path.startswith(resource_filter):
            continue
        ops = apidef[path]
        if not ops:
            continue
        found = True

        console.print("RESOURCE")
        console.print(f"  {path}")
        console.print()
        console.print("METHODS:")

        for op in ops:
            method = op["method"].upper()
            console.print(f"  {method}")
            console.print()

            desc = op.get("description", "")
            if desc:
                console.print("  DESCRIPTION:")
                console.print(f"    {desc}")
                console.print()

            q_params = op.get("query_parameters", [])
            if q_params:
                console.print("  QUERY PARAMETERS")
                for p in q_params:
                    p_desc = p.get("description", "")
                    line = f"    {p['name']}: {p_desc}" if p_desc else f"    {p['name']}"
                    console.print(line)
                console.print()

            p_params = op.get("post_parameters", [])
            if p_params:
                console.print("  PROPERTIES")
                for p in p_params:
                    p_desc = p.get("description", "")
                    line = f"    {p['name']}: {p_desc}" if p_desc else f"    {p['name']}"
                    console.print(line)
                console.print()

    if not found:
        console.print("(no endpoints found)")


def format_summary_csv(apidef: dict[str, Any]) -> str:
    """エンドポイント一覧を CSV 文字列で返す。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["method", "path", "query_parameters", "post_parameters"])
    for path in sorted(apidef.keys()):
        for op in apidef[path]:
            q_names = ";".join(p["name"] for p in op.get("query_parameters", []))
            p_names = ";".join(p["name"] for p in op.get("post_parameters", []))
            writer.writerow([op["method"].upper(), path, q_names, p_names])
    return buf.getvalue()


def format_endpoint_detail(
    apidef: dict[str, Any],
    method: str,
    template: str,
) -> str:
    """特定メソッド+パスのエンドポイント詳細を文字列で返す。"""
    ops = apidef.get(template, [])
    op = next((o for o in ops if o["method"] == method), None)
    if op is None:
        return f"{method.upper()} {template}: not defined"

    lines = [f"{method.upper()} {template}"]
    if op.get("query_parameters"):
        lines.append("  Query parameters:")
        for p in op["query_parameters"]:
            lines.append(f"    {_format_param(p, '-q')}")
    if op.get("post_parameters"):
        lines.append("  Body parameters:")
        for p in op["post_parameters"]:
            lines.append(f"    {_format_param(p, '-p')}")
    if not op.get("query_parameters") and not op.get("post_parameters"):
        lines.append("  (no parameters)")
    return "\n".join(lines)
