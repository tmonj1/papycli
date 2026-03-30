"""シェル補完ロジックとスクリプト生成。

補完の仕組み:
  bash/zsh スクリプトが `papycli _complete <current_index> <words...>` を呼び出す。
  `_complete` コマンドが補完候補を 1 行 1 候補の形式で標準出力に返す。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SAFE_CMD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_PLACEHOLDER_RE = re.compile(r"\{[^}]+\}")

METHODS = ["get", "post", "put", "patch", "delete"]
CONFIG_SUBCOMMANDS = ["add", "alias", "completion-script", "list", "log", "remove", "use"]
TOP_LEVEL_COMMANDS = METHODS + ["config", "spec", "summary"]

# ---------------------------------------------------------------------------
# シェルスクリプトテンプレート
# ---------------------------------------------------------------------------

_BASH_TEMPLATE = """\
_@@SAFENAME@@_completion() {
    local IFS=$'\\n'
    COMPREPLY=($(@@CMDNAME@@ _complete "${COMP_CWORD}" "${COMP_WORDS[@]}" 2>/dev/null))
    if [[ ${#COMPREPLY[@]} -eq 0 \\
          && "${COMP_WORDS[1]}" == "config" \\
          && "${COMP_WORDS[2]}" == "add" \\
          && "${COMP_CWORD}" -eq 3 ]]; then
        COMPREPLY=($(compgen -f -- "${COMP_WORDS[COMP_CWORD]}"))
        compopt -o filenames 2>/dev/null
    fi
}
complete -o nospace -F _@@SAFENAME@@_completion @@CMDNAME@@
"""

_ZSH_TEMPLATE = """\
_@@SAFENAME@@() {
    local -a completions
    completions=(${(f)"$(@@CMDNAME@@ _complete "$((CURRENT - 1))" "${words[@]}" 2>/dev/null)"})
    if [[ ${#completions[@]} -gt 0 ]]; then
        _describe '' completions
    elif [[ "${words[2]}" == "config" && "${words[3]}" == "add" && $CURRENT -eq 4 ]]; then
        _files
    fi
}
compdef _@@SAFENAME@@ @@CMDNAME@@
"""


def _render_script(template: str, cmd: str) -> str:
    """テンプレート内の @@CMDNAME@@ / @@SAFENAME@@ をコマンド名で置換する。

    @@...@@ は有効なエイリアス名 ([A-Za-z0-9_-]+) に含まれない @ を含むため、
    cmd の値に関わらずプレースホルダーが意図せず再置換されることはない。
    """
    safe = cmd.replace("-", "_")
    return template.replace("@@CMDNAME@@", cmd).replace("@@SAFENAME@@", safe)


# 後方互換用エイリアス
BASH_SCRIPT = _render_script(_BASH_TEMPLATE, "papycli")
ZSH_SCRIPT = _render_script(_ZSH_TEMPLATE, "papycli")


def generate_script(shell: str, cmd_name: str = "papycli") -> str:
    """指定シェル向けの補完スクリプトを返す。

    Args:
        shell: "bash" または "zsh"
        cmd_name: 補完対象のコマンド名。エイリアスで呼び出した場合はエイリアス名を渡す。

    Raises:
        ValueError: cmd_name に安全でない文字が含まれる場合。
    """
    # Windows の ".exe" / ".py" 等の拡張子を除去する
    cmd_name = Path(cmd_name).stem
    if not _SAFE_CMD_RE.match(cmd_name):
        raise ValueError(
            f"Invalid command name '{cmd_name}': must start with a letter or digit,"
            " and contain only letters, digits, hyphens, and underscores."
        )
    if shell == "bash":
        return _render_script(_BASH_TEMPLATE, cmd_name)
    return _render_script(_ZSH_TEMPLATE, cmd_name)


# ---------------------------------------------------------------------------
# 補完ロジック（純粋関数 — apidef を引数で受け取る）
# ---------------------------------------------------------------------------


def _find_op(apidef: dict[str, Any], method: str, resource: str) -> dict[str, Any] | None:
    """resource にマッチするテンプレートを探し、指定 method の operation を返す。"""
    from papycli.api_call import match_path_template

    match = match_path_template(resource, list(apidef.keys()))
    if match is None:
        return None
    template, _ = match
    return next((o for o in apidef[template] if o["method"] == method), None)


def _complete_resources(apidef: dict[str, Any], method: str, incomplete: str) -> list[str]:
    return [
        p
        for p in sorted(apidef.keys())
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
        "-q",
        "-p",
        "-d",
        "-H",
        "--summary",
        "-v",
        "--verbose",
        "--check",
        "--check-strict",
        "--response-check",
    ]
    if op is not None:
        if not op.get("query_parameters"):
            opts = [o for o in opts if o != "-q"]
        if not op.get("post_parameters"):
            opts = [o for o in opts if o not in ("-p", "-d")]
    return [o for o in opts if o.startswith(incomplete)]


# ---------------------------------------------------------------------------
# 静的補完スクリプト生成
# ---------------------------------------------------------------------------

_STATIC_BASH_TEMPLATE = """\
_@@SAFENAME@@_completion() {
    local cur prev pprev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev=""
    pprev=""
    [[ $COMP_CWORD -ge 1 ]] && prev="${COMP_WORDS[COMP_CWORD-1]}"
    [[ $COMP_CWORD -ge 2 ]] && pprev="${COMP_WORDS[COMP_CWORD-2]}"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=($(compgen -W @@TOP_LEVEL_CMDS@@ -- "$cur"))
        return
    fi

    local cmd="${COMP_WORDS[1]}"

    if [[ "$cmd" == "config" ]]; then
        case ${COMP_CWORD} in
            2)  COMPREPLY=($(compgen -W @@CONFIG_SUBCMDS@@ -- "$cur")) ;;
            3)  case "${COMP_WORDS[2]}" in
                    remove|use) COMPREPLY=($(compgen -W @@API_NAMES@@ -- "$cur")) ;;
                    add)        COMPREPLY=($(compgen -f -- "$cur"))
                                compopt -o filenames 2>/dev/null ;;
                esac ;;
        esac
        return
    fi

    if [[ "$cmd" == "summary" && ${COMP_CWORD} -eq 2 ]]; then
        COMPREPLY=($(compgen -W @@SUMMARY_OPTS@@ -- "$cur"))
        return
    fi

    if [[ "$cmd" == "spec" ]]; then
        if [[ ${COMP_CWORD} -eq 2 ]]; then
            COMPREPLY=($(compgen -W @@SPEC_OPTS@@ -- "$cur"))
        elif [[ ${COMP_CWORD} -eq 3 && "${COMP_WORDS[2]}" == "--full" ]]; then
            COMPREPLY=($(compgen -W @@ALL_RESOURCES@@ -- "$cur"))
        fi
        return
    fi

    case "$cmd" in get|post|put|patch|delete) ;; *) return ;; esac

    if [[ ${COMP_CWORD} -eq 2 ]]; then
        case "$cmd" in
@@METHOD_RESOURCE_CASES@@
        esac
        return
    fi

    local resource="${COMP_WORDS[2]}"
    local ctx="${cmd}:${resource}"

    # ここから extglob パターン（+([^ /])）を使う case 文があるため extglob を有効化する。
    # もともと無効だった場合のみ有効化し、各 return の直前で元の状態に戻す。
    shopt -q extglob; local _extglob_off=$?
    (( _extglob_off )) && shopt -s extglob

    if [[ "$prev" == "-q" ]]; then
        case "$ctx" in
@@Q_PARAM_CASES@@
        esac
        (( _extglob_off )) && shopt -u extglob
        return
    fi

    if [[ "$pprev" == "-q" ]]; then
        local pname="${prev%\\*}"
        case "${ctx}:${pname}" in
@@Q_ENUM_CASES@@
        esac
        (( _extglob_off )) && shopt -u extglob
        return
    fi

    if [[ "$prev" == "-p" ]]; then
        case "$ctx" in
@@P_PARAM_CASES@@
        esac
        (( _extglob_off )) && shopt -u extglob
        return
    fi

    if [[ "$pprev" == "-p" ]]; then
        local pname="${prev%\\*}"
        case "${ctx}:${pname}" in
@@P_ENUM_CASES@@
        esac
        (( _extglob_off )) && shopt -u extglob
        return
    fi

    (( _extglob_off )) && shopt -u extglob
    local _opts="-q -p -d -H --summary -v --verbose --check --check-strict --response-check"
    COMPREPLY=($(compgen -W "$_opts" -- "$cur"))
}

complete -o nospace -F _@@SAFENAME@@_completion @@CMDNAME@@
"""

_STATIC_ZSH_TEMPLATE = """\
_@@SAFENAME@@() {
    local cur="${words[CURRENT]}"
    local prev="${words[CURRENT-1]:-}"
    local pprev="${words[CURRENT-2]:-}"
    local cword=$((CURRENT - 1))
    local -a _c

    if [[ $cword -eq 1 ]]; then
        _c=(@@TOP_LEVEL_CMDS_ZSH@@)
        _describe 'command' _c && return
    fi

    local cmd="${words[2]}"

    if [[ "$cmd" == "config" ]]; then
        case $cword in
            2)  _c=(@@CONFIG_SUBCMDS_ZSH@@)
                _describe 'subcommand' _c ;;
            3)  case "${words[3]}" in
                    remove|use) _c=(@@API_NAMES_ZSH@@); _describe 'api' _c ;;
                    add)        _files ;;
                esac ;;
        esac
        return
    fi

    if [[ "$cmd" == "summary" && $cword -eq 2 ]]; then
        _c=(--csv @@ALL_RESOURCES_ZSH@@)
        _describe 'resource' _c
        return
    fi

    if [[ "$cmd" == "spec" ]]; then
        if [[ $cword -eq 2 ]]; then
            _c=(--full @@ALL_RESOURCES_ZSH@@)
            _describe 'resource' _c
        elif [[ $cword -eq 3 && "${words[3]}" == "--full" ]]; then
            _c=(@@ALL_RESOURCES_ZSH@@)
            _describe 'resource' _c
        fi
        return
    fi

    case "$cmd" in get|post|put|patch|delete) ;; *) return ;; esac

    if [[ $cword -eq 2 ]]; then
        case "$cmd" in
@@ZSH_METHOD_RESOURCE_CASES@@
        esac
        return
    fi

    local resource="${words[3]}"
    local ctx="${cmd}:${resource}"

    if [[ "$prev" == "-q" ]]; then
        case "$ctx" in
@@ZSH_Q_PARAM_CASES@@
        esac
        return
    fi

    if [[ "$pprev" == "-q" ]]; then
        local pname="${prev%\\*}"
        case "${ctx}:${pname}" in
@@ZSH_Q_ENUM_CASES@@
        esac
        return
    fi

    if [[ "$prev" == "-p" ]]; then
        case "$ctx" in
@@ZSH_P_PARAM_CASES@@
        esac
        return
    fi

    if [[ "$pprev" == "-p" ]]; then
        local pname="${prev%\\*}"
        case "${ctx}:${pname}" in
@@ZSH_P_ENUM_CASES@@
        esac
        return
    fi

    _c=(-q -p -d -H --summary -v --verbose --check --check-strict --response-check)
    _describe 'option' _c
}
compdef _@@SAFENAME@@ @@CMDNAME@@
"""


def _replace_placeholders(template: str, replacements: dict[str, str]) -> str:
    """テンプレート内のプレースホルダーを一括で安全に置換する。

    str.replace() を複数回呼ぶと置換済みテキストが再走査され、
    データ内に @@...@@ 形式の文字列が含まれる場合に意図しない展開が起こりえる。
    re.sub の一括置換により、置換テキストが再走査されないことを保証する。
    """
    pattern = re.compile("|".join(re.escape(k) for k in replacements))
    return pattern.sub(lambda m: replacements[m.group(0)], template)


def _shell_single_quote(s: str) -> str:
    """任意の文字列をシェルの単一クォートリテラルに変換する。

    単一クォート内では変数展開やコマンド置換が行われないため、
    スペース・$()・バッククォート等が含まれていても安全なリテラルとして使用できる。
    文字列中の単一クォートは '\"'\"' の形で閉じて再度開くことで表現する。
    """
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _case_pattern(s: str, shell: str = "bash") -> str:
    """bash/zsh の case パターンとして安全に埋め込めるリテラル文字列を返す。

    `{placeholder}` 形式のパステンプレート変数はシェルに応じたワイルドカードに変換する。
    - bash: extglob `+([^ /])` — スラッシュ・スペース以外の1文字以上（shopt -s extglob が必要）
    - zsh: `[^/ ][^/ ]*` — 標準グロブで同等の意味（setopt 不要）

    プレースホルダーを含まない文字列は従来どおり単一クォートのリテラルとして返す。
    """
    parts = _PLACEHOLDER_RE.split(s)
    if len(parts) == 1:
        return _shell_single_quote(s)
    wildcard = "+([^ /])" if shell == "bash" else "[^/ ][^/ ]*"
    return wildcard.join(_shell_single_quote(p) for p in parts)


def _shell_word_list(items: list[str]) -> str:
    """スペース区切りの単語列を単一クォートで囲んで返す（bash compgen -W 用）。"""
    return _shell_single_quote(" ".join(items))


def _zsh_array_elems(items: list[str]) -> str:
    """zsh 配列リテラルの要素部分（括弧なし）を返す。"""
    return " ".join(_shell_single_quote(w) for w in items)


def _bash_method_resource_cases(apidef: dict[str, Any]) -> str:
    lines: list[str] = []
    for method in ("get", "post", "put", "patch", "delete"):
        resources = sorted(
            p for p, ops in apidef.items() if any(o["method"] == method for o in ops)
        )
        if resources:
            wl = _shell_word_list(resources)
            lines.append(f'            {method}) COMPREPLY=($(compgen -W {wl} -- "$cur")) ;;')
    lines.append("            *) ;;")
    return "\n".join(lines)


def _build_param_names(params: list[dict[str, Any]]) -> list[str]:
    """required パラメータに * を付けてリストを返す。"""
    return [p["name"] + "*" for p in params if p.get("required")] + [
        p["name"] for p in params if not p.get("required")
    ]


def _bash_param_cases(apidef: dict[str, Any], kind: str) -> str:
    key = "query_parameters" if kind == "query" else "post_parameters"
    lines: list[str] = []
    for path in sorted(apidef):
        for op in apidef[path]:
            params = op.get(key, [])
            if not params:
                continue
            method = op["method"]
            names = _build_param_names(params)
            wl = _shell_word_list(names)
            pat = _case_pattern(f"{method}:{path}", shell="bash")
            lines.append(f'            {pat}) COMPREPLY=($(compgen -W {wl} -- "$cur")) ;;')
    lines.append("            *) ;;")
    return "\n".join(lines)


def _bash_enum_cases(apidef: dict[str, Any], kind: str) -> str:
    key = "query_parameters" if kind == "query" else "post_parameters"
    lines: list[str] = []
    for path in sorted(apidef):
        for op in apidef[path]:
            method = op["method"]
            for p in op.get(key, []):
                if "enum" not in p:
                    continue
                vals = [str(v) for v in p["enum"]]
                wl = _shell_word_list(vals)
                pname = p["name"]
                pat = _case_pattern(f"{method}:{path}:{pname}", shell="bash")
                lines.append(f'            {pat}) COMPREPLY=($(compgen -W {wl} -- "$cur")) ;;')
    lines.append("            *) ;;")
    return "\n".join(lines)


def _zsh_method_resource_cases(apidef: dict[str, Any]) -> str:
    lines: list[str] = []
    for method in ("get", "post", "put", "patch", "delete"):
        resources = sorted(
            p for p, ops in apidef.items() if any(o["method"] == method for o in ops)
        )
        if resources:
            ae = _zsh_array_elems(resources)
            lines.append(f"            {method}) _c=({ae}); _describe 'resource' _c ;;")
    lines.append("            *) ;;")
    return "\n".join(lines)


def _zsh_param_cases(apidef: dict[str, Any], kind: str) -> str:
    key = "query_parameters" if kind == "query" else "post_parameters"
    lines: list[str] = []
    for path in sorted(apidef):
        for op in apidef[path]:
            params = op.get(key, [])
            if not params:
                continue
            method = op["method"]
            names = _build_param_names(params)
            ae = _zsh_array_elems(names)
            pat = _case_pattern(f"{method}:{path}", shell="zsh")
            lines.append(f"            {pat}) _c=({ae}); _describe '' _c ;;")
    lines.append("            *) ;;")
    return "\n".join(lines)


def _zsh_enum_cases(apidef: dict[str, Any], kind: str) -> str:
    key = "query_parameters" if kind == "query" else "post_parameters"
    lines: list[str] = []
    for path in sorted(apidef):
        for op in apidef[path]:
            method = op["method"]
            for p in op.get(key, []):
                if "enum" not in p:
                    continue
                vals = [str(v) for v in p["enum"]]
                ae = _zsh_array_elems(vals)
                pname = p["name"]
                pat = _case_pattern(f"{method}:{path}:{pname}", shell="zsh")
                lines.append(f"            {pat}) _c=({ae}); _describe '' _c ;;")
    lines.append("            *) ;;")
    return "\n".join(lines)


def generate_static_script(
    shell: str,
    cmd_name: str,
    apidef: dict[str, Any] | None,
    api_names: list[str] | None,
) -> str:
    """補完データ埋め込み済みの静的シェル補完スクリプトを返す。

    Args:
        shell: "bash" または "zsh"
        cmd_name: 補完対象のコマンド名
        apidef: API 定義 dict。None の場合は API 固有の補完候補なし。
        api_names: 登録済み API 名リスト。None の場合は空。

    Raises:
        ValueError: shell が "bash" / "zsh" 以外、または cmd_name に安全でない文字が含まれる場合。

    Note:
        動的補完（`_complete` サブコマンド呼び出し）と比べた既知の制限:
        - 操作にクエリ/ボディパラメータがなくても -q / -p / -d は常に表示される。
        - `summary <resource> <TAB>` での --csv 補完は行われない（位置 2 のみ対応）。
        - スペースを含む API 名は bash での補完が正しく動作しない場合がある。
    """
    cmd_name = Path(cmd_name).stem
    if not _SAFE_CMD_RE.match(cmd_name):
        raise ValueError(
            f"Invalid command name '{cmd_name}': must start with a letter or digit,"
            " and contain only letters, digits, hyphens, and underscores."
        )
    safe = cmd_name.replace("-", "_")
    names = api_names or []
    adef = apidef or {}
    all_resources = sorted(adef.keys())

    if shell == "bash":
        return _replace_placeholders(
            _STATIC_BASH_TEMPLATE,
            {
                "@@CMDNAME@@": cmd_name,
                "@@SAFENAME@@": safe,
                "@@TOP_LEVEL_CMDS@@": _shell_word_list(TOP_LEVEL_COMMANDS),
                "@@CONFIG_SUBCMDS@@": _shell_word_list(CONFIG_SUBCOMMANDS),
                "@@API_NAMES@@": _shell_word_list(names),
                "@@SUMMARY_OPTS@@": _shell_word_list(["--csv"] + all_resources),
                "@@SPEC_OPTS@@": _shell_word_list(["--full"] + all_resources),
                "@@ALL_RESOURCES@@": _shell_word_list(all_resources),
                "@@METHOD_RESOURCE_CASES@@": _bash_method_resource_cases(adef),
                "@@Q_PARAM_CASES@@": _bash_param_cases(adef, "query"),
                "@@Q_ENUM_CASES@@": _bash_enum_cases(adef, "query"),
                "@@P_PARAM_CASES@@": _bash_param_cases(adef, "body"),
                "@@P_ENUM_CASES@@": _bash_enum_cases(adef, "body"),
            },
        )

    if shell != "zsh":
        raise ValueError(f"Unsupported shell '{shell}': must be 'bash' or 'zsh'.")

    return _replace_placeholders(
        _STATIC_ZSH_TEMPLATE,
        {
            "@@CMDNAME@@": cmd_name,
            "@@SAFENAME@@": safe,
            "@@TOP_LEVEL_CMDS_ZSH@@": _zsh_array_elems(TOP_LEVEL_COMMANDS),
            "@@CONFIG_SUBCMDS_ZSH@@": _zsh_array_elems(CONFIG_SUBCOMMANDS),
            "@@API_NAMES_ZSH@@": _zsh_array_elems(names),
            "@@ALL_RESOURCES_ZSH@@": _zsh_array_elems(all_resources),
            "@@ZSH_METHOD_RESOURCE_CASES@@": _zsh_method_resource_cases(adef),
            "@@ZSH_Q_PARAM_CASES@@": _zsh_param_cases(adef, "query"),
            "@@ZSH_Q_ENUM_CASES@@": _zsh_enum_cases(adef, "query"),
            "@@ZSH_P_PARAM_CASES@@": _zsh_param_cases(adef, "body"),
            "@@ZSH_P_ENUM_CASES@@": _zsh_enum_cases(adef, "body"),
        },
    )


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
