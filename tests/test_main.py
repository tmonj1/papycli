"""CLI エントリポイントのテスト."""

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from papycli import __version__
from papycli.main import cli

PETSTORE_PATH = Path(__file__).parent.parent / "examples" / "petstore-oas3.json"

MINIMAL_SPEC: dict[str, Any] = {
    "openapi": "3.0.2",
    "servers": [{"url": "http://localhost:9000/api"}],
    "paths": {
        "/items": {
            "get": {
                "parameters": [
                    {"name": "q", "in": "query", "required": False, "schema": {"type": "string"}}
                ]
            }
        }
    },
}


@pytest.fixture()
def minimal_spec_file(tmp_path: Path) -> Path:
    path = tmp_path / "myapi.json"
    path.write_text(json.dumps(MINIMAL_SPEC), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 基本動作
# ---------------------------------------------------------------------------


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "papycli" in result.output


def test_no_args_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage" in result.output


# ---------------------------------------------------------------------------
# papycli init
# ---------------------------------------------------------------------------


def test_cmd_init_success(tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(minimal_spec_file)])
    assert result.exit_code == 0
    assert "Initialized API 'myapi'" in result.output
    assert "http://localhost:9000/api" in result.output


def test_cmd_init_creates_conf(tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["init", str(minimal_spec_file)])
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["default"] == "myapi"
    assert conf["myapi"]["url"] == "http://localhost:9000/api"


def test_cmd_init_creates_apidef(tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["init", str(minimal_spec_file)])
    apidef_path = tmp_path / "apis" / "myapi.json"
    assert apidef_path.exists()


def test_cmd_init_nonexistent_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "no_such.json")])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# papycli use
# ---------------------------------------------------------------------------


def test_cmd_use_switches_default(tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    # 2 つの API を登録
    spec2 = tmp_path / "otherapi.json"
    spec2.write_text(json.dumps({**MINIMAL_SPEC, "servers": [{"url": "http://other"}]}), encoding="utf-8")
    runner.invoke(cli, ["init", str(minimal_spec_file)])
    runner.invoke(cli, ["init", str(spec2)])

    result = runner.invoke(cli, ["use", "myapi"])
    assert result.exit_code == 0
    assert "myapi" in result.output

    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["default"] == "myapi"


def test_cmd_use_unknown_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["use", "unknown"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# papycli conf
# ---------------------------------------------------------------------------


def test_cmd_conf_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["conf"])
    assert result.exit_code == 0
    assert str(tmp_path) in result.output


def test_cmd_conf_after_init(tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["init", str(minimal_spec_file)])
    result = runner.invoke(cli, ["conf"])
    assert result.exit_code == 0
    assert "myapi" in result.output
    assert "http://localhost:9000/api" in result.output
