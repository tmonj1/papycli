"""設定ファイル (papycli.conf) の読み書き."""

import json
import os
from pathlib import Path
from typing import Any

CONF_FILENAME = "papycli.conf"
APIS_DIRNAME = "apis"


def get_conf_dir() -> Path:
    """設定ディレクトリを返す。PAPYCLI_CONF_DIR 環境変数 or ~/.papycli"""
    env = os.environ.get("PAPYCLI_CONF_DIR")
    if env:
        return Path(env)
    return Path.home() / ".papycli"


def get_conf_path(conf_dir: Path | None = None) -> Path:
    return (conf_dir or get_conf_dir()) / CONF_FILENAME


def get_apis_dir(conf_dir: Path | None = None) -> Path:
    return (conf_dir or get_conf_dir()) / APIS_DIRNAME


def load_conf(conf_dir: Path | None = None) -> dict[str, Any]:
    """設定ファイルを読み込む。存在しない場合は空の dict を返す。"""
    path = get_conf_path(conf_dir)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def save_conf(conf: dict[str, Any], conf_dir: Path | None = None) -> None:
    """設定ファイルを保存する。ディレクトリが存在しない場合は作成する。"""
    path = get_conf_path(conf_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2, ensure_ascii=False)
        f.write("\n")


def register_api(
    conf: dict[str, Any],
    name: str,
    openapispec: str,
    apidef: str,
    url: str,
) -> None:
    """設定に API エントリを追加・更新する。default が未設定の場合は自動設定する。"""
    conf[name] = {"openapispec": openapispec, "apidef": apidef, "url": url}
    if "default" not in conf:
        conf["default"] = name


def set_default_api(conf: dict[str, Any], name: str) -> None:
    """デフォルト API を変更する。"""
    conf["default"] = name


def get_default_api(conf: dict[str, Any]) -> str | None:
    """現在のデフォルト API 名を返す。未設定の場合は None。"""
    return conf.get("default")  # type: ignore[return-value]


def load_current_apidef(conf_dir: Path | None = None) -> tuple[dict[str, Any], str]:
    """現在のデフォルト API の (apidef dict, base_url) を返す。"""
    resolved_dir = conf_dir or get_conf_dir()
    conf = load_conf(resolved_dir)
    api_name = get_default_api(conf)
    if not api_name:
        raise RuntimeError("No default API configured. Run 'papycli config add <spec>' first.")

    api_entry = conf.get(api_name)
    if not isinstance(api_entry, dict):
        raise RuntimeError(f"Invalid configuration for API '{api_name}'.")

    base_url = str(api_entry.get("url", ""))
    apidef_filename = str(api_entry.get("apidef", f"{api_name}.json"))
    apidef_path = get_apis_dir(resolved_dir) / apidef_filename

    if not apidef_path.exists():
        raise RuntimeError(
            f"API definition file not found: {apidef_path}\n"
            "Run 'papycli config add <spec>' to regenerate it."
        )

    with apidef_path.open(encoding="utf-8") as f:
        apidef: dict[str, Any] = json.load(f)
    return apidef, base_url
