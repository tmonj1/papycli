"""summary モジュールのテスト。"""

import io
from typing import Any

from papycli.summary import (
    build_rows,
    format_endpoint_detail,
    format_summary_csv,
    print_summary,
)

# ---------------------------------------------------------------------------
# テスト用 apidef
# ---------------------------------------------------------------------------

APIDEF: dict[str, Any] = {
    "/pet": [
        {
            "method": "post",
            "query_parameters": [],
            "post_parameters": [
                {"name": "name", "type": "string", "required": True},
                {"name": "status", "type": "string", "required": False,
                 "enum": ["available", "pending", "sold"]},
                {"name": "photoUrls", "type": "array", "required": True},
            ],
        }
    ],
    "/pet/findByStatus": [
        {
            "method": "get",
            "query_parameters": [
                {"name": "status", "type": "string", "required": False,
                 "enum": ["available", "pending", "sold"]},
            ],
            "post_parameters": [],
        }
    ],
    "/pet/{petId}": [
        {"method": "get", "query_parameters": [], "post_parameters": []},
        {"method": "delete", "query_parameters": [], "post_parameters": []},
    ],
    "/store/inventory": [
        {"method": "get", "query_parameters": [], "post_parameters": []}
    ],
}


# ---------------------------------------------------------------------------
# build_rows
# ---------------------------------------------------------------------------


def test_build_rows_returns_all_endpoints() -> None:
    rows = build_rows(APIDEF)
    methods_paths = {(r[0], r[1]) for r in rows}
    assert ("POST", "/pet") in methods_paths
    assert ("GET", "/pet/findByStatus") in methods_paths
    assert ("GET", "/pet/{petId}") in methods_paths
    assert ("DELETE", "/pet/{petId}") in methods_paths
    assert ("GET", "/store/inventory") in methods_paths


def test_build_rows_sorted_by_path() -> None:
    rows = build_rows(APIDEF)
    paths = [r[1] for r in rows]
    assert paths == sorted(paths)


def test_build_rows_filter() -> None:
    rows = build_rows(APIDEF, resource_filter="/pet")
    paths = {r[1] for r in rows}
    assert "/store/inventory" not in paths
    assert "/pet" in paths
    assert "/pet/findByStatus" in paths
    assert "/pet/{petId}" in paths


def test_build_rows_filter_exact() -> None:
    rows = build_rows(APIDEF, resource_filter="/store")
    paths = {r[1] for r in rows}
    assert "/store/inventory" in paths
    assert "/pet" not in paths


def test_build_rows_no_match_filter() -> None:
    rows = build_rows(APIDEF, resource_filter="/nonexistent")
    assert rows == []


def test_build_rows_required_annotation() -> None:
    rows = build_rows(APIDEF)
    post_row = next(r for r in rows if r[0] == "POST" and r[1] == "/pet")
    assert "-p name*" in post_row[2]


def test_build_rows_optional_no_star() -> None:
    rows = build_rows(APIDEF)
    post_row = next(r for r in rows if r[0] == "POST" and r[1] == "/pet")
    # status is optional — no star
    assert "-p status[" in post_row[2]
    assert "-p status*" not in post_row[2]


def test_build_rows_array_annotation() -> None:
    rows = build_rows(APIDEF)
    post_row = next(r for r in rows if r[0] == "POST" and r[1] == "/pet")
    assert "-p photoUrls*[]" in post_row[2]


def test_build_rows_enum_annotation() -> None:
    rows = build_rows(APIDEF)
    get_row = next(r for r in rows if r[0] == "GET" and r[1] == "/pet/findByStatus")
    assert "-q status[available|pending|sold]" in get_row[2]


def test_build_rows_no_params_empty_string() -> None:
    rows = build_rows(APIDEF)
    inv_row = next(r for r in rows if r[1] == "/store/inventory")
    assert inv_row[2] == ""


# ---------------------------------------------------------------------------
# print_summary
# ---------------------------------------------------------------------------


def test_print_summary_contains_paths() -> None:
    buf = io.StringIO()
    print_summary(APIDEF, file=buf)
    output = buf.getvalue()
    assert "/pet" in output
    assert "/store/inventory" in output


def test_print_summary_contains_methods() -> None:
    buf = io.StringIO()
    print_summary(APIDEF, file=buf)
    output = buf.getvalue()
    assert "POST" in output
    assert "GET" in output
    assert "DELETE" in output


def test_print_summary_filtered() -> None:
    buf = io.StringIO()
    print_summary(APIDEF, resource_filter="/store", file=buf)
    output = buf.getvalue()
    assert "/store/inventory" in output
    assert "/pet" not in output


def test_print_summary_empty_apidef() -> None:
    buf = io.StringIO()
    print_summary({}, file=buf)
    output = buf.getvalue()
    assert "no endpoints" in output


# ---------------------------------------------------------------------------
# format_summary_csv
# ---------------------------------------------------------------------------


def test_format_summary_csv_header() -> None:
    csv_str = format_summary_csv(APIDEF)
    first_line = csv_str.splitlines()[0]
    assert first_line == "method,path,query_parameters,post_parameters"


def test_format_summary_csv_contains_rows() -> None:
    csv_str = format_summary_csv(APIDEF)
    assert "GET,/pet/findByStatus,status," in csv_str
    assert "GET,/store/inventory,," in csv_str


def test_format_summary_csv_post_params() -> None:
    csv_str = format_summary_csv(APIDEF)
    # POST /pet の post_parameters に name, status, photoUrls が含まれる
    post_line = next(l for l in csv_str.splitlines() if l.startswith("POST,/pet,"))
    assert "name" in post_line
    assert "status" in post_line
    assert "photoUrls" in post_line


def test_format_summary_csv_sorted_by_path() -> None:
    csv_str = format_summary_csv(APIDEF)
    lines = [l for l in csv_str.splitlines()[1:] if l]
    paths = [l.split(",")[1] for l in lines]
    assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# format_endpoint_detail
# ---------------------------------------------------------------------------


def test_format_endpoint_detail_with_params() -> None:
    detail = format_endpoint_detail(APIDEF, "get", "/pet/findByStatus")
    assert "GET /pet/findByStatus" in detail
    assert "Query parameters" in detail
    assert "-q status" in detail
    assert "available" in detail


def test_format_endpoint_detail_no_params() -> None:
    detail = format_endpoint_detail(APIDEF, "get", "/store/inventory")
    assert "GET /store/inventory" in detail
    assert "no parameters" in detail


def test_format_endpoint_detail_post_body() -> None:
    detail = format_endpoint_detail(APIDEF, "post", "/pet")
    assert "POST /pet" in detail
    assert "Body parameters" in detail
    assert "-p name*" in detail


def test_format_endpoint_detail_not_found() -> None:
    detail = format_endpoint_detail(APIDEF, "patch", "/pet")
    assert "not defined" in detail
