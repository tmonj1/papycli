"""シェル補完ロジックとスクリプト生成。

補完の仕組み:
  bash/zsh スクリプトが `papycli _complete <current_index> <words...>` を呼び出す。
  `_complete` コマンドが補完候補を 1 行 1 候補の形式で標準出力に返す。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

METHODS = ["get", "post", "put", "patch", "delete"]
CONFIG_SUBCOMMANDS = ["add", "alias", "completion-script", "list", "log", "remove", "use"]
TOP_LEVEL_COMMANDS = METHODS + ["config", "spec", "summary"]

# ---------------------------------------------------------------------------
# シェルスクリプトテンプレート
# ---------------------------------------------------------------------------

_BASH_TEMPLATE = """\
_SAFENAME_completion() {
    local IFS=$'\\n'
    COMPREPLY=($(CMDNAME _complete "${COMP_CWORD}" "${COMP_WORDS[@]}" 2>/dev/null))
    if [[ ${#COMPREPLY[@]} -eq 0 \\
          && "${COMP_WORDS[1]}" == "config" \\
          && "${COMP_WORDS[2]}" == "add" \\
          && "${COMP_CWORD}" -eq 3 ]]; then
        COMPREPLY=($(compgen -f -- "${COMP_WORDS[COMP_CWORD]}"))
        compopt -o filenames 2>/dev/null
    fi
}
complete -o nospace -F _SAFENAME_completion CMDNAME
"""

_ZSH_TEMPLATE = """\
_SAFENAME() {
    local -a completions
    completions=(${(f)"$(CMDNAME _complete "$((CURRENT - 1))" "${words[@]}" 2>/dev/null)"})
    if [[ ${#completions[@]} -gt 0 ]]; then
        _describe '' completions
    elif [[ "${words[2]}" == "config" && "${words[3]}" == "add" && $CURRENT -eq 4 ]]; then
        _files
    fi
}
compdef _SAFENAME CMDNAME
"""


def _render_script(template: str, cmd: str) -> str:
    """テンプレート内の CMDNAME / SAFENAME をコマンド名で置換する。"""
    safe = cmd.replace("-", "_")
    return template.replace("CMDNAME", cmd).replace("SAFENAME", safe)


# 後方互換用エイリアス
BASH_SCRIPT = _render_script(_BASH_TEMPLATE, "papycli")
ZSH_SCRIPT = _render_script(_ZSH_TEMPLATE, "papycli")


def generate_script(shell: str, cmd_name: str = "papycli") -> str:
    """指定シェル向けの補完スクリプトを返す。

    Args:
        shell: "bash" または "zsh"
        cmd_name: 補完対象のコマンド名。エイリアスで呼び出した場合はエイリアス名を渡す。
    """
    if shell == "bash":
        return _render_script(_BASH_TEMPLATE, cmd_name)
    return _render_script(_ZSH_TEMPLATE, cmd_name)


# ---------------------------------------------------------------------------
# 補完ロジック（純粋関数 — apidef を引数で受け取る）
# ---------------------------------------------------------------------------


def _find_op(
    apidef: dict[str, Any], method: str, resource: str
) -> dict[str, Any] | None:
    """resource にマッチするテンプレートを探し、指定 method の operation を返す。"""
    from papycli.api_call import match_path_template

    match = match_path_template(resource, list(apidef.keys()))
    if match is None:
        return None
    template, _ = match
    return next((o for o in apidef[template] if o["method"] == method), None)


def _complete_resources(apidef: dict[str, Any], method: str, incomplete: str) -> list[str]:
    return [
        p for p in sorted(apidef.keys())
        if p.startswith(incomplete) and any(o["method"] == method for o in apidef[p])
    ]


def _used_param_names(words: list[str], flag: str) -> set[str]:
    """words 中で flag NAME( VALUE) のパターンで使用済みのパラメータ名を返す。"""
    used: set[str] = set()
    i = 0
    while i < len(words):
        if words[i] == flag and i + 1 < len(words):
            name = words[i + 1]
            # NAME が別のオプションフラグでも空文字でもない場合のみ使用済みとして扱う
            # 補完で選択された場合に末尾に * が付いていることがあるため取り除いてから登録する
            if name and not name.startswith("-"):
                used.add(name.removesuffix("*"))
            # flag と NAME までは確実に読み飛ばすが、VALUE は仮定しない
            i += 2
        else:
            i += 1
    return used


def _complete_param_names(
    apidef: dict[str, Any],
    method: str,
    resource: str,
    kind: str,
    incomplete: str,
    used: set[str] | None = None,
) -> list[str]:
    op = _find_op(apidef, method, resource)
    if op is None:
        return []
    key = "query_parameters" if kind == "query" else "post_parameters"
    # incomplete の末尾 * を取り除いてからパラメータ名と比較する
    incomplete_stripped = incomplete.removesuffix("*")
    required: list[str] = []
    optional: list[str] = []
    for p in op.get(key, []):
        name = p["name"]
        if not name.startswith(incomplete_stripped):
            continue
        if used is not None and name in used:
            continue
        if p.get("required", False):
            required.append(name + "*")
        else:
            optional.append(name)
    return required + optional


def _complete_enum_values(
    apidef: dict[str, Any],
    method: str,
    resource: str,
    kind: str,
    param_name: str,
    incomplete: str,
) -> list[str]:
    op = _find_op(apidef, method, resource)
    if op is None:
        return []
    key = "query_parameters" if kind == "query" else "post_parameters"
    # 補完で選択された場合、param_name の末尾に * が付いていることがあるため取り除く
    normalized_name = param_name.removesuffix("*")
    for p in op.get(key, []):
        if p["name"] == normalized_name and "enum" in p:
            return [str(v) for v in p["enum"] if str(v).startswith(incomplete)]
    return []


def completions_for_context(
    words: list[str],
    current: int,
    apidef: dict[str, Any] | None,
    api_names: list[str] | None = None,
) -> list[str]:
    """コマンドラインのコンテキストに応じた補完候補を返す。

    Args:
        words:     コマンドライントークンのリスト（words[0] = "papycli"）
        current:   補完中の単語のインデックス（0 始まり）
        apidef:    現在の API 定義 dict。リソースパスやパラメータの補完に使用する。
                   None の場合、それらの補完は空リストを返す（トップレベルや
                   config サブコマンドの補完は apidef なしでも機能する）。
        api_names: 登録済み API 名のリスト。config remove / config use の補完に使用する。
                   None の場合、それらのサブコマンドは補完候補を返さない。
    """
    incomplete = words[current] if current < len(words) else ""

    # トップレベルサブコマンド名の補完
    if current == 1:
        return [c for c in TOP_LEVEL_COMMANDS if c.startswith(incomplete)]

    if len(words) < 2:
        return []

    # config サブコマンドの補完
    if words[1] == "config":
        if current == 2:
            return [c for c in CONFIG_SUBCOMMANDS if c.startswith(incomplete)]
        if (
            current == 3
            and len(words) > 2
            and words[2] in ("remove", "use")
            and api_names is not None
        ):
            return [n for n in api_names if n.startswith(incomplete)]
        return []

    # summary コマンドの補完
    if words[1] == "summary":
        if current == 2:
            candidates: list[str] = []
            if apidef is not None:
                candidates = [p for p in sorted(apidef.keys()) if p.startswith(incomplete)]
            if "--csv".startswith(incomplete):
                candidates.append("--csv")
            return candidates
        if current == 3 and (len(words) <= 2 or words[2] != "--csv"):
            return ["--csv"] if "--csv".startswith(incomplete) else []
        return []

    # spec コマンドの補完
    if words[1] == "spec":
        if current == 2:
            candidates = ["--full"] if "--full".startswith(incomplete) else []
            if apidef is not None:
                candidates += [p for p in sorted(apidef.keys()) if p.startswith(incomplete)]
            return candidates
        # spec --full <TAB> → リソースパスを補完
        if current == 3 and len(words) > 2 and words[2] == "--full":
            if apidef is not None:
                return [p for p in sorted(apidef.keys()) if p.startswith(incomplete)]
        return []

    # words[1] が HTTP メソッドでない場合は補完なし
    if words[1] not in METHODS:
        return []

    method = words[1]

    # リソースパスの補完
    if current == 2:
        if apidef is None:
            return []
        return _complete_resources(apidef, method, incomplete)

    resource = words[2] if len(words) > 2 else ""
    prev = words[current - 1] if current >= 1 else ""
    prev_prev = words[current - 2] if current >= 2 else ""

    if apidef is None:
        return []

    # -q NAME → クエリパラメータ名
    if prev == "-q":
        return _complete_param_names(
            apidef, method, resource, "query", incomplete, _used_param_names(words[:current], "-q")
        )

    # -q NAME VALUE → enum 値
    if prev_prev == "-q":
        return _complete_enum_values(apidef, method, resource, "query", prev, incomplete)

    # -p NAME → ボディパラメータ名
    if prev == "-p":
        return _complete_param_names(
            apidef, method, resource, "body", incomplete, _used_param_names(words[:current], "-p")
        )

    # -p NAME VALUE → enum 値
    if prev_prev == "-p":
        return _complete_enum_values(apidef, method, resource, "body", prev, incomplete)

    # オプション名（エンドポイントのパラメータ有無に応じてフィルタリング）
    op = _find_op(apidef, method, resource)
    opts: list[str] = [
        "-q", "-p", "-d", "-H", "--summary", "-v", "--verbose",
        "--check", "--check-strict", "--response-check",
    ]
    if op is not None:
        if not op.get("query_parameters"):
            opts = [o for o in opts if o != "-q"]
        if not op.get("post_parameters"):
            opts = [o for o in opts if o not in ("-p", "-d")]
    return [o for o in opts if o.startswith(incomplete)]


def get_completions(words: list[str], current: int, conf_dir: Path | None = None) -> list[str]:
    """apidef と conf をディスクから読み込んで補完候補を返す。

    読み込みに失敗した場合でも、トップレベルコマンドおよび config サブコマンド自体の補完は行われる。
    conf や apidef に依存する補完（config remove / config use での API 名候補や、
    メソッド・リソース・オプション等の API 定義由来の候補）は、対応するデータが読み込めなかった
    場合は空になる。
    """
    from papycli.config import get_conf_dir, load_conf, load_current_apidef

    resolved_dir = conf_dir or get_conf_dir()

    try:
        conf = load_conf(resolved_dir)
        api_names: list[str] | None = [
            k for k in conf if k not in ("default", "aliases") and isinstance(conf[k], dict)
        ]
    except Exception:
        api_names = None

    try:
        apidef, _ = load_current_apidef(resolved_dir)
    except Exception:
        apidef = None

    return completions_for_context(words, current, apidef, api_names)
