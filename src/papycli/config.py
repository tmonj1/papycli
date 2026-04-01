"""設定ファイル (papycli.conf) の読み書き."""

import json
import os
import tempfile
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
    """設定ファイルを保存する。ディレクトリが存在しない場合は作成する。

    一時ファイルに書き込んでから atomic rename することで、書き込み途中の
    失敗でも既存の設定ファイルが壊れないようにする。
    """
    path = get_conf_path(conf_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".papycli.conf.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(conf, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


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


def remove_api(conf: dict[str, Any], name: str) -> None:
    """設定から API エントリを削除し、必要に応じてデフォルト API を更新する。

    削除した API がデフォルトだった場合、残りの API の中から先頭のものを新しい
    デフォルトに設定する。残りがなければ "default" キーを削除する。
    """
    is_default = conf.get("default") == name
    del conf[name]
    if is_default:
        _reserved = ("default", "aliases")
        remaining = [k for k in conf if k not in _reserved and isinstance(conf[k], dict)]
        if remaining:
            conf["default"] = remaining[0]
        else:
            conf.pop("default", None)


def set_default_api(conf: dict[str, Any], name: str) -> None:
    """デフォルト API を変更する。"""
    conf["default"] = name


_api_override: str | None = None


def set_api_override(name: str | None) -> None:
    """エイリアス呼び出し時に使用するスペック名を上書き設定する。"""
    global _api_override
    _api_override = name


def get_default_api(conf: dict[str, Any]) -> str | None:
    """現在のデフォルト API 名を返す。未設定・空文字列・非文字列の場合は None。

    ``set_api_override`` が設定されている場合はそちらを優先する。
    """
    if _api_override is not None:
        return _api_override
    value = conf.get("default")
    if isinstance(value, str) and value:
        return value
    return None


def get_aliases(conf: dict[str, Any]) -> dict[str, str]:
    """エイリアス名 → スペック名のマッピングを返す。未設定の場合は空の dict。"""
    value = conf.get("aliases")
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, str)}
    return {}


def set_alias(conf: dict[str, Any], alias_name: str, spec_name: str) -> None:
    """エイリアスを設定する。"""
    if "aliases" not in conf or not isinstance(conf["aliases"], dict):
        conf["aliases"] = {}
    conf["aliases"][alias_name] = spec_name


def remove_alias(conf: dict[str, Any], alias_name: str) -> None:
    """エイリアスを削除する。存在しない場合は何もしない。"""
    aliases = conf.get("aliases")
    if isinstance(aliases, dict):
        aliases.pop(alias_name, None)
        if not aliases:
            conf.pop("aliases")


def get_logfile(conf: dict[str, Any]) -> str | None:
    """現在のログファイルパスを返す。未設定・空文字列・非文字列の場合は None。"""
    value = conf.get("logfile")
    if isinstance(value, str) and value:
        return value
    return None


def set_logfile(conf: dict[str, Any], path: str) -> None:
    """ログファイルのパスを設定する。"""
    conf["logfile"] = path


def unset_logfile(conf: dict[str, Any]) -> None:
    """ログファイル設定を削除する（ログ無効化）。"""
    conf.pop("logfile", None)


def load_current_apidef(
    conf_dir: Path | None = None,
    *,
    conf: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """現在のデフォルト API の (apidef dict, base_url) を返す。

    ``conf`` を渡すと設定ファイルの再読み込みをスキップする。
    """
    resolved_dir = conf_dir or get_conf_dir()
    if conf is None:
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


def load_current_raw_spec(
    conf_dir: Path | None = None,
    *,
    conf: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """現在のデフォルト API の生 OpenAPI spec dict を返す。

    ``papycli config add`` 時に保存された ``{api_name}.spec.json`` を読み込む。

    Args:
        conf: 呼び出し元で既に読み込み済みの設定 dict。指定時は load_conf() の呼び出しを省略する。
    """
    resolved_dir = conf_dir or get_conf_dir()
    if conf is None:
        conf = load_conf(resolved_dir)
    api_name = get_default_api(conf)
    if not api_name:
        raise RuntimeError("No default API configured. Run 'papycli config add <spec>' first.")

    api_entry = conf.get(api_name)
    if not isinstance(api_entry, dict):
        raise RuntimeError(f"Invalid configuration for API '{api_name}'.")

    spec_path = get_apis_dir(resolved_dir) / f"{api_name}.spec.json"
    if not spec_path.exists():
        raise RuntimeError(
            f"Raw spec file not found: {spec_path}\n"
            "Run 'papycli config add <spec>' to regenerate it."
        )

    with spec_path.open(encoding="utf-8") as f:
        raw_spec: dict[str, Any] = json.load(f)
    return raw_spec
