"""--summary / --summary-csv の出力処理。"""

import csv
import io
from typing import Any, TextIO

from rich.console import Console
from rich.table import Table


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
    """エンドポイント一覧を rich テーブルで出力する。"""
    rows = build_rows(apidef, resource_filter)
    if not rows:
        click_echo = print if file is None else lambda s: file.write(s + "\n")
        click_echo("(no endpoints found)")
        return

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        pad_edge=False,
        show_edge=False,
    )
    table.add_column("METHOD", min_width=8)
    table.add_column("PATH", min_width=24)
    table.add_column("PARAMETERS")
    for method, path, params in rows:
        table.add_row(method, path, params)

    Console(file=file, highlight=False, no_color=(file is not None)).print(table)


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
