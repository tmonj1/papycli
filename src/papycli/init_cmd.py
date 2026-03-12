"""--init コマンドの処理: OpenAPI spec を内部形式に変換して保存する。"""

import json
from pathlib import Path

from papycli.config import get_apis_dir, register_api
from papycli.spec_loader import extract_base_url, load_spec, resolve_refs, spec_to_apidef


def init_api(spec_path: Path, conf_dir: Path) -> tuple[str, str]:
    """OpenAPI spec を読み込み、内部形式に変換して保存する。

    Returns:
        (api_name, base_url) のタプル
    """
    raw_spec = load_spec(spec_path)
    resolved_spec = resolve_refs(raw_spec, raw_spec)
    apidef = spec_to_apidef(resolved_spec)

    api_name = spec_path.stem
    base_url = extract_base_url(resolved_spec)

    apis_dir = get_apis_dir(conf_dir)
    apis_dir.mkdir(parents=True, exist_ok=True)

    apidef_path = apis_dir / f"{api_name}.json"
    with apidef_path.open("w", encoding="utf-8") as f:
        json.dump(apidef, f, indent=2, ensure_ascii=False)
        f.write("\n")

    spec_path_out = apis_dir / f"{api_name}.spec.json"
    with spec_path_out.open("w", encoding="utf-8") as f:
        json.dump(raw_spec, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return api_name, base_url


def register_initialized_api(
    conf: dict,  # type: ignore[type-arg]
    api_name: str,
    spec_path: Path,
    base_url: str,
) -> None:
    """init 後に設定ファイルへ API エントリを登録する。"""
    spec_filename = spec_path.name
    apidef_filename = f"{api_name}.json"
    register_api(conf, api_name, spec_filename, apidef_filename, base_url)
