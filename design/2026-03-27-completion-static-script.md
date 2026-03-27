# Shell Completion 高速化（静的スクリプト生成）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `config completion-script` が補完データを埋め込んだ静的 bash/zsh スクリプトを出力するようにし、Tab 補完時の Python プロセス起動をゼロにする。

**Architecture:** `completion.py` に `generate_static_script(shell, cmd_name, apidef, api_names)` を追加する。この関数はリソースパス・パラメータ名・enum 値を shell の case 文として埋め込んだ完全な補完スクリプトを返す。`main.py` の `cmd_config_completion_script` がこの関数を呼ぶよう変更する。ユーザーの利用方法（`eval "$(papycli config completion-script bash)"`）は変わらない。既存の `generate_script` と `_complete` サブコマンドは後方互換のため残す。

**Tech Stack:** Python 3.12, bash 3.x+, zsh 5.x+, pytest, ruff, mypy

---

## ファイル変更マップ

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/papycli/completion.py` | 追加 | 静的テンプレート・データ構築ヘルパー・`generate_static_script` |
| `src/papycli/main.py` | 変更 | `cmd_config_completion_script` が `generate_static_script` を呼ぶ |
| `tests/unittest/test_completion.py` | 追加 | `TestGenerateStaticScript` クラス |
| `tests/unittest/test_main.py` | 追加 | `TestCompletionScriptStatic` クラス |

---

## Task 1: `generate_static_script` と補完データ構築ヘルパーの追加

**Files:**
- Modify: `src/papycli/completion.py`
- Modify: `tests/unittest/test_completion.py`

- [ ] **Step 1-1: 失敗するテストを書く**

`tests/unittest/test_completion.py` の末尾にクラスを追加する。ファイル先頭の既存 import ブロックに `generate_static_script` を追加する（新しい `from` 行は追加しない）。

```python
# 既存 import ブロックに追加（既存行は省略）:
from papycli.completion import (
    CONFIG_SUBCOMMANDS,
    TOP_LEVEL_COMMANDS,
    _used_param_names,
    completions_for_context,
    generate_script,
    generate_static_script,  # ← 追加
)
```

ファイル末尾に以下のクラスを追加する:

```python
class TestGenerateStaticScript:
    def test_bash_contains_resources(self) -> None:
        script = generate_static_script("bash", "papycli", APIDEF, ["petstore"])
        assert "/pet/findByStatus" in script
        assert "/pet/{petId}" in script

    def test_bash_contains_api_names(self) -> None:
        script = generate_static_script("bash", "papycli", APIDEF, ["petstore", "myapi"])
        assert "petstore" in script
        assert "myapi" in script

    def test_bash_contains_enum_values(self) -> None:
        script = generate_static_script("bash", "papycli", APIDEF, ["petstore"])
        assert "available" in script
        assert "pending" in script
        assert "sold" in script

    def test_bash_contains_required_param_marker(self) -> None:
        script = generate_static_script("bash", "papycli", APIDEF, ["petstore"])
        # POST /pet の name は required → name* が含まれる
        assert "name*" in script

    def test_bash_has_completion_function_and_binding(self) -> None:
        script = generate_static_script("bash", "papycli", APIDEF, ["petstore"])
        assert "_papycli_completion()" in script
        assert "complete -o nospace -F _papycli_completion papycli" in script

    def test_bash_no_python_call(self) -> None:
        script = generate_static_script("bash", "papycli", APIDEF, ["petstore"])
        assert "_complete" not in script

    def test_bash_none_apidef_generates_valid_script(self) -> None:
        script = generate_static_script("bash", "papycli", None, None)
        assert "_papycli_completion()" in script
        assert "get post put patch delete" in script
        assert "_complete" not in script

    def test_bash_custom_cmd_name(self) -> None:
        script = generate_static_script("bash", "petcli", APIDEF, ["petstore"])
        assert "_petcli_completion()" in script
        assert "complete -o nospace -F _petcli_completion petcli" in script

    def test_zsh_has_compdef(self) -> None:
        script = generate_static_script("zsh", "papycli", APIDEF, ["petstore"])
        assert "compdef _papycli papycli" in script
        assert "/pet/findByStatus" in script

    def test_zsh_no_python_call(self) -> None:
        script = generate_static_script("zsh", "papycli", APIDEF, ["petstore"])
        assert "_complete" not in script

    def test_zsh_contains_enum_values(self) -> None:
        script = generate_static_script("zsh", "papycli", APIDEF, ["petstore"])
        assert "available" in script
```

- [ ] **Step 1-2: テスト実行（失敗確認）**

```bash
uv run pytest tests/unittest/test_completion.py::TestGenerateStaticScript -v 2>&1 | head -20
```

Expected: `ImportError` または `cannot import name 'generate_static_script'`

- [ ] **Step 1-3: `completion.py` に実装を追加する**

`src/papycli/completion.py` のファイル末尾（`get_completions` 関数の後）に以下を追加する。

```python
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
        COMPREPLY=($(compgen -W "get post put patch delete config spec summary" -- "$cur"))
        return
    fi

    local cmd="${COMP_WORDS[1]}"

    if [[ "$cmd" == "config" ]]; then
        case ${COMP_CWORD} in
            2)  COMPREPLY=($(compgen -W "add alias completion-script list log remove use" -- "$cur")) ;;
            3)  case "${COMP_WORDS[2]}" in
                    remove|use) COMPREPLY=($(compgen -W "@@API_NAMES@@" -- "$cur")) ;;
                    add)        COMPREPLY=($(compgen -f -- "$cur"))
                                compopt -o filenames 2>/dev/null ;;
                esac ;;
        esac
        return
    fi

    if [[ "$cmd" == "summary" && ${COMP_CWORD} -eq 2 ]]; then
        COMPREPLY=($(compgen -W "--csv @@ALL_RESOURCES@@" -- "$cur"))
        return
    fi

    if [[ "$cmd" == "spec" ]]; then
        if [[ ${COMP_CWORD} -eq 2 ]]; then
            COMPREPLY=($(compgen -W "--full @@ALL_RESOURCES@@" -- "$cur"))
        elif [[ ${COMP_CWORD} -eq 3 && "${COMP_WORDS[2]}" == "--full" ]]; then
            COMPREPLY=($(compgen -W "@@ALL_RESOURCES@@" -- "$cur"))
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

    if [[ "$prev" == "-q" ]]; then
        case "$ctx" in
@@Q_PARAM_CASES@@
        esac
        return
    fi

    if [[ "$pprev" == "-q" ]]; then
        local pname="${prev%\\*}"
        case "${ctx}:${pname}" in
@@Q_ENUM_CASES@@
        esac
        return
    fi

    if [[ "$prev" == "-p" ]]; then
        case "$ctx" in
@@P_PARAM_CASES@@
        esac
        return
    fi

    if [[ "$pprev" == "-p" ]]; then
        local pname="${prev%\\*}"
        case "${ctx}:${pname}" in
@@P_ENUM_CASES@@
        esac
        return
    fi

    COMPREPLY=($(compgen -W "-q -p -d -H --summary -v --verbose --check --check-strict --response-check" -- "$cur"))
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
        _c=(get post put patch delete config spec summary)
        _describe 'command' _c && return
    fi

    local cmd="${words[2]}"

    if [[ "$cmd" == "config" ]]; then
        case $cword in
            2)  _c=(add alias completion-script list log remove use)
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


def _shell_word_list(items: list[str]) -> str:
    """スペース区切りの単語列をダブルクォートで囲んで返す（bash compgen -W 用）。"""
    escaped = " ".join(w.replace("\\", "\\\\").replace('"', '\\"') for w in items)
    return f'"{escaped}"'


def _zsh_array_elems(items: list[str]) -> str:
    """zsh 配列リテラルの要素部分（括弧なし）を返す。"""
    return " ".join(f'"{w}"' for w in items)


def _bash_method_resource_cases(apidef: dict[str, Any]) -> str:
    lines: list[str] = []
    for method in ("get", "post", "put", "patch", "delete"):
        resources = sorted(
            p for p, ops in apidef.items() if any(o["method"] == method for o in ops)
        )
        if resources:
            lines.append(
                f'            {method}) COMPREPLY=($(compgen -W {_shell_word_list(resources)} -- "$cur")) ;;'
            )
    return "\n".join(lines)


def _build_param_names(params: list[dict[str, Any]]) -> list[str]:
    """required パラメータに * を付けてリストを返す。"""
    return (
        [p["name"] + "*" for p in params if p.get("required")]
        + [p["name"] for p in params if not p.get("required")]
    )


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
            lines.append(
                f'            "{method}:{path}") COMPREPLY=($(compgen -W {_shell_word_list(names)} -- "$cur")) ;;'
            )
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
                lines.append(
                    f'            "{method}:{path}:{p["name"]}") COMPREPLY=($(compgen -W {_shell_word_list(vals)} -- "$cur")) ;;'
                )
    return "\n".join(lines)


def _zsh_method_resource_cases(apidef: dict[str, Any]) -> str:
    lines: list[str] = []
    for method in ("get", "post", "put", "patch", "delete"):
        resources = sorted(
            p for p, ops in apidef.items() if any(o["method"] == method for o in ops)
        )
        if resources:
            lines.append(
                f"            {method}) _c=({_zsh_array_elems(resources)}); _describe 'resource' _c ;;"
            )
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
            lines.append(
                f'            "{method}:{path}") _c=({_zsh_array_elems(names)}); _describe \'\' _c ;;'
            )
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
                lines.append(
                    f'            "{method}:{path}:{p["name"]}") _c=({_zsh_array_elems(vals)}); _describe \'\' _c ;;'
                )
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
        ValueError: cmd_name に安全でない文字が含まれる場合。
    """
    cmd_name = Path(cmd_name).stem
    if not _SAFE_CMD_RE.match(cmd_name):
        raise ValueError(
            f"Invalid command name '{cmd_name}': "
            "must start with a letter or digit, and contain only letters, digits, hyphens, and underscores."
        )
    safe = cmd_name.replace("-", "_")
    names = api_names or []
    adef = apidef or {}
    all_resources = sorted(adef.keys())

    if shell == "bash":
        script = _STATIC_BASH_TEMPLATE
        script = script.replace("@@CMDNAME@@", cmd_name)
        script = script.replace("@@SAFENAME@@", safe)
        script = script.replace("@@API_NAMES@@", " ".join(names))
        script = script.replace("@@ALL_RESOURCES@@", " ".join(all_resources))
        script = script.replace("@@METHOD_RESOURCE_CASES@@", _bash_method_resource_cases(adef))
        script = script.replace("@@Q_PARAM_CASES@@", _bash_param_cases(adef, "query"))
        script = script.replace("@@Q_ENUM_CASES@@", _bash_enum_cases(adef, "query"))
        script = script.replace("@@P_PARAM_CASES@@", _bash_param_cases(adef, "body"))
        script = script.replace("@@P_ENUM_CASES@@", _bash_enum_cases(adef, "body"))
        return script

    # zsh
    script = _STATIC_ZSH_TEMPLATE
    script = script.replace("@@CMDNAME@@", cmd_name)
    script = script.replace("@@SAFENAME@@", safe)
    script = script.replace("@@API_NAMES_ZSH@@", _zsh_array_elems(names))
    script = script.replace("@@ALL_RESOURCES_ZSH@@", _zsh_array_elems(all_resources))
    script = script.replace("@@ZSH_METHOD_RESOURCE_CASES@@", _zsh_method_resource_cases(adef))
    script = script.replace("@@ZSH_Q_PARAM_CASES@@", _zsh_param_cases(adef, "query"))
    script = script.replace("@@ZSH_Q_ENUM_CASES@@", _zsh_enum_cases(adef, "query"))
    script = script.replace("@@ZSH_P_PARAM_CASES@@", _zsh_param_cases(adef, "body"))
    script = script.replace("@@ZSH_P_ENUM_CASES@@", _zsh_enum_cases(adef, "body"))
    return script
```

- [ ] **Step 1-4: テスト実行（成功確認）**

```bash
uv run pytest tests/unittest/test_completion.py::TestGenerateStaticScript -v
```

Expected: 11 tests PASS

- [ ] **Step 1-5: ruff + mypy チェック**

```bash
uv run ruff check src/papycli/completion.py && uv run mypy src/papycli/completion.py
```

Expected: no errors / warnings

- [ ] **Step 1-6: コミット**

```bash
git add src/papycli/completion.py tests/unittest/test_completion.py
git commit -m "feat: add generate_static_script for Python-free shell completion"
```

---

## Task 2: `cmd_config_completion_script` を静的スクリプト生成に切り替える

**Files:**
- Modify: `src/papycli/main.py`
- Modify: `tests/unittest/test_main.py`

- [ ] **Step 2-1: 失敗するテストを書く**

`tests/unittest/test_main.py` の末尾に追加する。

```python
class TestCompletionScriptStatic:
    def test_bash_no_python_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """生成スクリプトに _complete 呼び出しが含まれないこと。"""
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "completion-script", "bash"])
        assert result.exit_code == 0
        assert "_complete" not in result.output
        assert "_papycli_completion()" in result.output

    def test_zsh_no_python_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "completion-script", "zsh"])
        assert result.exit_code == 0
        assert "_complete" not in result.output
        assert "compdef _papycli papycli" in result.output

    @pytest.mark.skipif(not PETSTORE_PATH.exists(), reason="petstore-oas3.json not found")
    def test_bash_with_apidef_contains_resources(
        self, petstore_conf_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """apidef がある場合、生成スクリプトにリソースパスが含まれること。"""
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(petstore_conf_dir))
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "completion-script", "bash"])
        assert result.exit_code == 0
        assert "/pet" in result.output
        assert "/store/inventory" in result.output
```

- [ ] **Step 2-2: テスト実行（失敗確認）**

```bash
uv run pytest tests/unittest/test_main.py::TestCompletionScriptStatic -v 2>&1 | head -20
```

Expected: `test_bash_no_python_call` が FAIL（現状のスクリプトに `_complete` が含まれるため）

- [ ] **Step 2-3: `main.py` の import と `cmd_config_completion_script` を更新する**

**import 行の変更：**

変更前（`main.py` の `completion` import 行）:
```python
from papycli.completion import _SAFE_CMD_RE, generate_script, get_completions
```

変更後:
```python
from papycli.completion import _SAFE_CMD_RE, generate_script, generate_static_script, get_completions
```

**関数本体の変更：**

変更前（`cmd_config_completion_script` 関数本体）:
```python
    root_name = click.get_current_context().find_root().info_name or ""
    cmd_name = Path(root_name).stem  # .stem で Windows の ".exe" 等を除去する
    try:
        click.echo(generate_script(shell, cmd_name), nl=False)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
```

変更後:
```python
    root_name = click.get_current_context().find_root().info_name or ""
    cmd_name = Path(root_name).stem  # .stem で Windows の ".exe" 等を除去する
    conf_dir = get_conf_dir()
    try:
        conf = load_conf(conf_dir)
        api_names: list[str] = [
            k for k in conf if k not in ("default", "aliases") and isinstance(conf[k], dict)
        ]
        apidef, _ = load_current_apidef(conf_dir, conf=conf)
    except Exception:
        api_names = []
        apidef = None
    try:
        click.echo(generate_static_script(shell, cmd_name, apidef, api_names), nl=False)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
```

- [ ] **Step 2-4: テスト実行（成功確認）**

```bash
uv run pytest tests/unittest/test_main.py::TestCompletionScriptStatic -v
```

Expected: 3 tests PASS

- [ ] **Step 2-5: 全ユニットテスト実行（既存テストの破損確認）**

```bash
uv run pytest tests/unittest/ -v
```

Expected: 全テスト PASS

- [ ] **Step 2-6: ruff + mypy チェック**

```bash
uv run ruff check src/papycli/main.py && uv run mypy src/papycli/main.py
```

Expected: no errors / warnings

- [ ] **Step 2-7: コミット**

```bash
git add src/papycli/main.py tests/unittest/test_main.py
git commit -m "feat: switch config completion-script to static script generation"
```

---

## Task 3: 全テスト実行と最終確認

**Files:** 変更なし

- [ ] **Step 3-1: 全テスト実行**

```bash
uv run pytest tests/ -v
```

Expected: 全テスト PASS

- [ ] **Step 3-2: 生成スクリプトの内容確認**

```bash
uv run papycli config completion-script bash 2>/dev/null | head -30
```

Expected: `_papycli_completion()` 関数の定義が出力される。`_complete` の文字列が含まれない。

- [ ] **Step 3-3: ruff 全体チェック**

```bash
uv run ruff check src/
```

Expected: no errors

---

## 移行メモ（実装者向け）

既存ユーザーが古いスクリプト（`papycli _complete` を呼ぶ動的版）を `.bashrc` に設定している場合、papycli をアップグレード後に以下を再実行する必要がある：

```bash
eval "$(papycli config completion-script bash)"   # bash
eval "$(papycli config completion-script zsh)"    # zsh
```

また、`config add`・`config use`・`config remove` で API 設定を変更した後も、補完候補を更新するために同コマンドを再実行する必要がある。
