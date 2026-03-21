"""統合テスト: 実際の subprocess + 実 HTTP サーバーで papycli の動作を検証する."""

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

PETSTORE_SPEC = Path(__file__).parent.parent.parent / "examples" / "petstore" / "petstore-oas3.json"
RunPapycli = Callable[..., subprocess.CompletedProcess[str]]

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# A: config add
# ---------------------------------------------------------------------------


def test_config_add_creates_files(run_papycli: RunPapycli, tmp_path: Path) -> None:
    """config add がコンフィグファイルと API 定義ファイルを生成する。"""
    result = run_papycli("config", "add", str(PETSTORE_SPEC))
    assert result.returncode == 0
    assert (tmp_path / "papycli.conf").exists()
    assert (tmp_path / "apis" / "petstore-oas3.json").exists()


def test_config_add_reserved_name_fails(run_papycli: RunPapycli, tmp_path: Path) -> None:
    """予約名 'default' のファイルは登録できない。"""
    minimal: dict[str, object] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://localhost:9000/api"}],
        "paths": {},
    }
    spec = tmp_path / "default.json"
    spec.write_text(json.dumps(minimal), encoding="utf-8")

    result = run_papycli("config", "add", str(spec))
    assert result.returncode != 0
    assert "default" in result.stdout or "default" in result.stderr
    assert not (tmp_path / "papycli.conf").exists()


# ---------------------------------------------------------------------------
# B: GET リクエスト
# ---------------------------------------------------------------------------


def test_get_inventory(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """GET リクエストが実際のサーバーに届き、レスポンスが出力される。"""
    registered_petstore.expect_request(
        "/api/v3/store/inventory", method="GET"
    ).respond_with_json({"available": 3})

    result = run_papycli("get", "/store/inventory")

    assert result.returncode == 0
    assert "available" in result.stdout
    registered_petstore.check_assertions()


def test_get_path_param_resolves(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """パスパラメータ（/pet/42）が /pet/{petId} テンプレートに展開される。"""
    registered_petstore.expect_request(
        "/api/v3/pet/42", method="GET"
    ).respond_with_json({"id": 42, "name": "Buddy", "photoUrls": []})

    result = run_papycli("get", "/pet/42")

    assert result.returncode == 0
    assert "Buddy" in result.stdout
    registered_petstore.check_assertions()


def test_get_query_param_forwarded(
    registered_petstore: HTTPServer, run_papycli: RunPapycli
) -> None:
    """-q で指定したクエリパラメータが URL に付与される。"""
    registered_petstore.expect_request(
        "/api/v3/pet/findByStatus",
        method="GET",
        query_string="status=available",
    ).respond_with_json([])

    result = run_papycli("get", "/pet/findByStatus", "-q", "status", "available")

    assert result.returncode == 0
    registered_petstore.check_assertions()


def test_get_verbose_shows_status(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """--verbose オプションで HTTP ステータス行が stdout に出力される。"""
    registered_petstore.expect_request(
        "/api/v3/store/inventory", method="GET"
    ).respond_with_json({"dogs": 1})

    result = run_papycli("get", "/store/inventory", "--verbose")

    assert result.returncode == 0
    assert "HTTP 200" in result.stdout


def test_get_non2xx_status_on_stderr(
    registered_petstore: HTTPServer, run_papycli: RunPapycli
) -> None:
    """非 2xx レスポンスはステータス行が stderr に出力される。"""
    registered_petstore.expect_request(
        "/api/v3/store/inventory", method="GET"
    ).respond_with_json({"message": "not found"}, status=404)

    result = run_papycli("get", "/store/inventory")

    assert result.returncode == 0
    assert "HTTP 404" in result.stderr


# ---------------------------------------------------------------------------
# C: POST リクエスト
# ---------------------------------------------------------------------------


def test_post_body_params_sent(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """-p で指定したパラメータが JSON ボディとしてサーバーに届く。"""
    registered_petstore.expect_request(
        "/api/v3/pet", method="POST"
    ).respond_with_json({"id": 99})

    result = run_papycli(
        "post", "/pet",
        "-p", "name", "Fido",
        "-p", "photoUrls", "http://example.com/img.jpg",
        "-p", "status", "available",
    )

    assert result.returncode == 0
    assert len(registered_petstore.log) == 1
    body = json.loads(registered_petstore.log[0][0].data)
    assert body["name"] == "Fido"
    assert body["status"] == "available"


def test_post_raw_body_sent(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """-d で指定した生 JSON ボディがそのままサーバーに届く。"""
    registered_petstore.expect_request(
        "/api/v3/pet", method="POST"
    ).respond_with_json({"id": 1})

    raw = json.dumps({"name": "Rex", "photoUrls": [], "status": "available"})
    result = run_papycli("post", "/pet", "-d", raw)

    assert result.returncode == 0
    body = json.loads(registered_petstore.log[0][0].data)
    assert body["name"] == "Rex"


def test_post_content_type_json(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """POST リクエストに Content-Type: application/json ヘッダーが付く。"""
    registered_petstore.expect_request(
        "/api/v3/pet", method="POST"
    ).respond_with_json({"id": 1})

    run_papycli("post", "/pet", "-p", "name", "Rex", "-p", "photoUrls", "http://x.com/a.jpg")

    assert len(registered_petstore.log) == 1
    ct = registered_petstore.log[0][0].content_type
    assert "application/json" in ct


# ---------------------------------------------------------------------------
# D: DELETE リクエスト
# ---------------------------------------------------------------------------


def test_delete_success(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """DELETE リクエストが成功する。"""
    registered_petstore.expect_request(
        "/api/v3/pet/5", method="DELETE"
    ).respond_with_data(b"", status=200)

    result = run_papycli("delete", "/pet/5")

    assert result.returncode == 0
    registered_petstore.check_assertions()


def test_delete_204_status_on_stderr(
    registered_petstore: HTTPServer, run_papycli: RunPapycli
) -> None:
    """204 No Content のステータス行が stderr に出力される。"""
    registered_petstore.expect_request(
        "/api/v3/pet/5", method="DELETE"
    ).respond_with_data(b"", status=204)

    result = run_papycli("delete", "/pet/5")

    assert result.returncode == 0
    assert "HTTP 204" in result.stderr


# ---------------------------------------------------------------------------
# E: --check-strict
# ---------------------------------------------------------------------------


def test_check_strict_aborts_no_request(
    registered_petstore: HTTPServer, run_papycli: RunPapycli
) -> None:
    """必須パラメータ不足時、--check-strict はリクエストを送信せず exit 1 する。"""
    # ハンドラーを登録しない — 到達したら HTTPServer がエラーを返す
    result = run_papycli("post", "/pet", "--check-strict")

    assert result.returncode == 1
    assert "missing" in result.stdout or "missing" in result.stderr
    # サーバーへリクエストが届いていないことを確認
    assert len(registered_petstore.log) == 0


# ---------------------------------------------------------------------------
# F: カスタムヘッダー
# ---------------------------------------------------------------------------


def test_custom_header_forwarded(registered_petstore: HTTPServer, run_papycli: RunPapycli) -> None:
    """-H で指定したヘッダーがサーバーに転送される。"""
    registered_petstore.expect_request(
        "/api/v3/store/inventory", method="GET"
    ).respond_with_json({})

    run_papycli("get", "/store/inventory", "-H", "X-Request-ID: test-abc")

    assert len(registered_petstore.log) == 1
    req_headers = registered_petstore.log[0][0].headers
    assert req_headers.get("X-Request-ID") == "test-abc"


def test_env_custom_header_forwarded(
    registered_petstore: HTTPServer, run_papycli: RunPapycli
) -> None:
    """PAPYCLI_CUSTOM_HEADER 環境変数で指定したヘッダーがサーバーに転送される。"""
    registered_petstore.expect_request(
        "/api/v3/store/inventory", method="GET"
    ).respond_with_json({})

    run_papycli(
        "get", "/store/inventory",
        extra_env={"PAPYCLI_CUSTOM_HEADER": "X-Tenant: acme"},
    )

    assert len(registered_petstore.log) == 1
    req_headers = registered_petstore.log[0][0].headers
    assert req_headers.get("X-Tenant") == "acme"


# ---------------------------------------------------------------------------
# G: summary / spec コマンド（HTTP サーバー不要）
# ---------------------------------------------------------------------------


def test_summary_lists_endpoints(run_papycli: RunPapycli) -> None:
    """summary コマンドがエンドポイント一覧を出力する。"""
    run_papycli("config", "add", str(PETSTORE_SPEC))
    result = run_papycli("summary")
    assert result.returncode == 0
    assert "/pet" in result.stdout
    assert "GET" in result.stdout or "get" in result.stdout


def test_spec_returns_valid_json(run_papycli: RunPapycli) -> None:
    """spec コマンドが有効な JSON を返す。"""
    run_papycli("config", "add", str(PETSTORE_SPEC))
    result = run_papycli("spec")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "/pet" in data


# ---------------------------------------------------------------------------
# H: エラーケース
# ---------------------------------------------------------------------------


def test_unknown_path_exits_nonzero(run_papycli: RunPapycli) -> None:
    """存在しないパスは非ゼロ終了する。"""
    run_papycli("config", "add", str(PETSTORE_SPEC))
    result = run_papycli("get", "/no/such/path")
    assert result.returncode != 0


def test_no_config_exits_nonzero(run_papycli: RunPapycli) -> None:
    """config が未設定の場合は非ゼロ終了する。"""
    result = run_papycli("get", "/pet/1")
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# I: 基本動作確認
# ---------------------------------------------------------------------------


def test_version_flag(run_papycli: RunPapycli) -> None:
    """--version が正常に動作する。"""
    result = run_papycli("--version")
    assert result.returncode == 0
    assert re.search(r"\d+\.\d+\.\d+", result.stdout)  # SemVer 形式チェック


def test_help_flag(run_papycli: RunPapycli) -> None:
    """--help が正常に動作する。"""
    result = run_papycli("--help")
    assert result.returncode == 0
    assert "papycli" in result.stdout
