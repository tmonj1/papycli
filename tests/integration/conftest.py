"""統合テスト用フィクスチャ."""

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

PROJECT_ROOT = Path(__file__).parent.parent.parent
PETSTORE_SPEC = PROJECT_ROOT / "examples" / "petstore" / "petstore-oas3.json"
_PAPYCLI_BIN = PROJECT_ROOT / ".venv" / "bin" / "papycli"

RunPapycli = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture(scope="session")
def papycli_bin() -> Path:
    """プロジェクト venv の papycli バイナリパスを返す。存在しない場合はスキップ。"""
    if not _PAPYCLI_BIN.exists():
        pytest.skip("papycli binary not found — run `uv sync` first")
    return _PAPYCLI_BIN


@pytest.fixture()
def run_papycli(papycli_bin: Path, tmp_path: Path) -> RunPapycli:
    """papycli をサブプロセスで実行するヘルパーを返す。

    PAPYCLI_CONF_DIR は tmp_path に隔離される。
    """

    def _run(
        *args: str, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        base_env: dict[str, str] = dict(os.environ)

        # テスト用サブプロセスではプロキシ設定を無効化し、ローカルホストへのアクセスをバイパスする
        _proxy_keys = (
            "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"
        )
        for key in _proxy_keys:
            base_env.pop(key, None)

        no_proxy = base_env.get("NO_PROXY") or base_env.get("no_proxy") or ""
        existing_hosts = {h.strip() for h in no_proxy.split(",") if h.strip()}
        merged_hosts = existing_hosts | {"localhost", "127.0.0.1"}
        base_env["NO_PROXY"] = ",".join(sorted(merged_hosts))

        env: dict[str, str] = {
            **base_env,
            "PAPYCLI_CONF_DIR": str(tmp_path),
            "VIRTUAL_ENV": str(PROJECT_ROOT / ".venv"),
        }
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(papycli_bin), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    return _run


@pytest.fixture()
def registered_petstore(
    run_papycli: RunPapycli, httpserver: HTTPServer, tmp_path: Path
) -> HTTPServer:
    """petstore spec を config add し、URL をテスト用 httpserver に差し替えた HTTPServer を返す。"""
    result = run_papycli("config", "add", str(PETSTORE_SPEC))
    assert result.returncode == 0, f"config add failed:\n{result.stderr}"

    conf_path = tmp_path / "papycli.conf"
    conf: dict[str, object] = json.loads(conf_path.read_text(encoding="utf-8"))
    api_name = conf["default"]
    assert isinstance(api_name, str)
    api_conf = conf[api_name]
    assert isinstance(api_conf, dict)
    api_conf["url"] = httpserver.url_for("/api/v3")
    conf_path.write_text(json.dumps(conf, indent=2, ensure_ascii=False), encoding="utf-8")

    return httpserver
