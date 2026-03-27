"""completion モジュールのテスト。"""

from typing import Any

from papycli.completion import (
    CONFIG_SUBCOMMANDS,
    TOP_LEVEL_COMMANDS,
    _used_param_names,
    completions_for_context,
    generate_script,
    generate_static_script,  # ← add this
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
        },
        {"method": "put", "query_parameters": [], "post_parameters": []},
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
    "/pet/findByTags": [
        {
            "method": "get",
            "query_parameters": [
                {"name": "tags", "type": "array", "required": True},
                {"name": "limit", "type": "integer", "required": False},
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


def ctx(words: list[str], current: int) -> list[str]:
    """completions_for_context のショートハンド。"""
    return completions_for_context(words, current, APIDEF)


def ctx_no_apidef(words: list[str], current: int) -> list[str]:
    return completions_for_context(words, current, None)


# ---------------------------------------------------------------------------
# サブコマンド補完 (current == 1)
# ---------------------------------------------------------------------------


def test_complete_subcommand_empty() -> None:
    result = ctx(["papycli", ""], 1)
    assert "get" in result
    assert "post" in result
    assert "delete" in result
    assert "config" in result
    assert "spec" in result
    assert "summary" in result
    assert "init" not in result


def test_complete_subcommand_prefix_g() -> None:
    result = ctx(["papycli", "g"], 1)
    assert result == ["get"]


def test_complete_subcommand_prefix_p() -> None:
    result = ctx(["papycli", "p"], 1)
    assert "post" in result
    assert "patch" in result
    assert "put" in result
    assert "get" not in result


def test_complete_subcommand_no_match() -> None:
    assert ctx(["papycli", "xyz"], 1) == []


def test_top_level_commands_covers_expected() -> None:
    assert set(TOP_LEVEL_COMMANDS) == {
        "get", "post", "put", "patch", "delete", "config", "spec", "summary"
    }


# ---------------------------------------------------------------------------
# リソースパス補完 (current == 2, method command)
# ---------------------------------------------------------------------------


def test_complete_resource_all() -> None:
    result = ctx(["papycli", "get", ""], 2)
    # /pet has only POST and PUT — must not appear for GET
    assert "/pet" not in result
    assert "/pet/findByStatus" in result
    assert "/store/inventory" in result


def test_complete_resource_method_filter_post() -> None:
    # /pet supports POST; /pet/findByStatus and /store/inventory do not
    result = ctx(["papycli", "post", ""], 2)
    assert "/pet" in result
    assert "/pet/findByStatus" not in result
    assert "/store/inventory" not in result


def test_complete_resource_prefix() -> None:
    result = ctx(["papycli", "get", "/pet/f"], 2)
    assert "/pet/findByStatus" in result
    assert "/store/inventory" not in result


def test_complete_resource_store() -> None:
    result = ctx(["papycli", "get", "/store"], 2)
    assert "/store/inventory" in result
    assert "/pet" not in result


def test_complete_resource_no_apidef() -> None:
    assert ctx_no_apidef(["papycli", "get", ""], 2) == []


def test_complete_config_subcommands_empty() -> None:
    result = ctx(["papycli", "config", ""], 2)
    assert "add" in result
    assert "remove" in result
    assert "use" in result
    assert "list" in result
    assert "completion-script" in result


def test_complete_config_subcommands_prefix() -> None:
    result = ctx(["papycli", "config", "l"], 2)
    assert "list" in result
    assert "add" not in result


def test_complete_config_subcommands_covers_all() -> None:
    assert set(CONFIG_SUBCOMMANDS) == {
        "add", "alias", "completion-script", "list", "log", "remove", "use",
    }


def test_complete_config_no_further_completion() -> None:
    # config add の引数は補完しない（api_names なし）
    result = ctx(["papycli", "config", "add", ""], 3)
    assert result == []


# ---------------------------------------------------------------------------
# config remove / config use — API 名補完
# ---------------------------------------------------------------------------

API_NAMES = ["petstore", "myapi", "other-api"]


def ctx_with_names(words: list[str], current: int) -> list[str]:
    return completions_for_context(words, current, APIDEF, API_NAMES)


def test_complete_config_remove_api_names() -> None:
    result = ctx_with_names(["papycli", "config", "remove", ""], 3)
    assert result == API_NAMES


def test_complete_config_remove_prefix() -> None:
    result = ctx_with_names(["papycli", "config", "remove", "pet"], 3)
    assert result == ["petstore"]


def test_complete_config_use_api_names() -> None:
    result = ctx_with_names(["papycli", "config", "use", ""], 3)
    assert result == API_NAMES


def test_complete_config_use_prefix() -> None:
    result = ctx_with_names(["papycli", "config", "use", "my"], 3)
    assert result == ["myapi"]


def test_complete_config_remove_no_api_names() -> None:
    """api_names が None の場合は空リスト（conf 読み込み失敗時）。"""
    result = completions_for_context(["papycli", "config", "remove", ""], 3, APIDEF, None)
    assert result == []


def test_complete_config_use_no_api_names() -> None:
    result = completions_for_context(["papycli", "config", "use", ""], 3, APIDEF, None)
    assert result == []


# ---------------------------------------------------------------------------
# summary コマンド補完
# ---------------------------------------------------------------------------


def test_complete_summary_resources() -> None:
    result = ctx(["papycli", "summary", ""], 2)
    assert "/pet/findByStatus" in result
    assert "/store/inventory" in result
    assert "--csv" in result


def test_complete_summary_resource_prefix() -> None:
    result = ctx(["papycli", "summary", "/pet"], 2)
    assert "/pet/findByStatus" in result
    assert "/store/inventory" not in result


def test_complete_summary_csv_after_resource() -> None:
    result = ctx(["papycli", "summary", "/pet", ""], 3)
    assert "--csv" in result


def test_complete_summary_nothing_after_csv() -> None:
    result = ctx(["papycli", "summary", "--csv", ""], 3)
    assert result == []


def test_complete_summary_no_apidef() -> None:
    result = ctx_no_apidef(["papycli", "summary", ""], 2)
    assert "--csv" in result
    assert "/pet" not in result


# ---------------------------------------------------------------------------
# クエリパラメータ名の補完 (-q NAME)
# ---------------------------------------------------------------------------


def test_complete_query_param_name() -> None:
    words = ["papycli", "get", "/pet/findByStatus", "-q", ""]
    result = ctx(words, 4)
    assert "status" in result


def test_complete_query_param_name_prefix() -> None:
    words = ["papycli", "get", "/pet/findByStatus", "-q", "st"]
    result = ctx(words, 4)
    assert "status" in result


def test_complete_query_param_name_no_params() -> None:
    words = ["papycli", "get", "/store/inventory", "-q", ""]
    result = ctx(words, 4)
    assert result == []


def test_complete_query_param_repeated_option() -> None:
    # -q status available -q <TAB> → status は使用済みなので除外される
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status", "available", "-q", ""]
    result = ctx(words, 7)
    assert "status" not in result


def test_complete_query_param_name_required_asterisk() -> None:
    """必須クエリパラメータは * 付きで返され先頭に並ぶ。"""
    words = ["papycli", "get", "/pet/findByTags", "-q", ""]
    result = ctx(words, 4)
    assert "tags*" in result
    assert "limit" in result
    assert result.index("tags*") < result.index("limit")


def test_complete_query_param_name_required_asterisk_prefix() -> None:
    """必須クエリパラメータのプレフィックス補完でも * が付く。"""
    words = ["papycli", "get", "/pet/findByTags", "-q", "t"]
    result = ctx(words, 4)
    assert "tags*" in result
    assert "limit" not in result


def test_complete_query_param_excludes_used_with_asterisk() -> None:
    """補完で tags* を選択後も使用済みとして正しく除外される。"""
    words = ["papycli", "get", "/pet/findByTags", "-q", "tags*", "foo", "-q", ""]
    result = ctx(words, 7)
    assert "tags*" not in result
    assert "limit" in result


# ---------------------------------------------------------------------------
# クエリパラメータ enum 値の補完 (-q NAME VALUE)
# ---------------------------------------------------------------------------


def test_complete_enum_value() -> None:
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status", ""]
    result = ctx(words, 5)
    assert "available" in result
    assert "pending" in result
    assert "sold" in result


def test_complete_enum_value_prefix() -> None:
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status", "a"]
    result = ctx(words, 5)
    assert "available" in result
    assert "pending" not in result


def test_complete_enum_value_no_enum() -> None:
    # photoUrls は enum なし
    words = ["papycli", "post", "/pet", "-p", "photoUrls", ""]
    result = ctx(words, 5)
    assert result == []


def test_complete_query_enum_value_with_asterisk_param_name() -> None:
    """-q status* <TAB> でも enum 値が補完される（* を除去して照合）。"""
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status*", ""]
    result = ctx(words, 5)
    assert "available" in result
    assert "pending" in result
    assert "sold" in result


# ---------------------------------------------------------------------------
# ボディパラメータ名の補完 (-p NAME)
# ---------------------------------------------------------------------------


def test_complete_body_param_name() -> None:
    words = ["papycli", "post", "/pet", "-p", ""]
    result = ctx(words, 4)
    # 必須パラメータは * 付きで返される
    assert "name*" in result
    assert "photoUrls*" in result
    # 任意パラメータは * なし
    assert "status" in result
    # 必須パラメータが任意パラメータより前に並ぶ
    assert result.index("name*") < result.index("status")
    assert result.index("photoUrls*") < result.index("status")


def test_complete_body_param_name_prefix() -> None:
    words = ["papycli", "post", "/pet", "-p", "n"]
    result = ctx(words, 4)
    assert "name*" in result
    assert "status" not in result


# ---------------------------------------------------------------------------
# ボディパラメータ enum 値の補完 (-p NAME VALUE)
# ---------------------------------------------------------------------------


def test_complete_body_enum_value() -> None:
    words = ["papycli", "post", "/pet", "-p", "status", ""]
    result = ctx(words, 5)
    assert "available" in result
    assert "pending" in result
    assert "sold" in result


# ---------------------------------------------------------------------------
# オプション名の補完
# ---------------------------------------------------------------------------


def test_complete_options_after_resource() -> None:
    # /store/inventory は query も body もパラメータなし → -q, -p, -d は除外される
    words = ["papycli", "get", "/store/inventory", ""]
    result = ctx(words, 3)
    assert "-q" not in result
    assert "-p" not in result
    assert "-d" not in result
    assert "--summary" in result
    assert "-v" in result
    assert "--verbose" in result
    assert "--check" in result
    assert "--check-strict" in result


def test_complete_options_prefix_dash() -> None:
    # /store/inventory はパラメータなし → -q は除外、-H や --summary は表示
    words = ["papycli", "get", "/store/inventory", "-"]
    result = ctx(words, 3)
    assert "-q" not in result
    assert "-H" in result
    assert "--summary" in result
    assert "-v" in result


def test_complete_options_prefix_double_dash() -> None:
    words = ["papycli", "get", "/store/inventory", "--"]
    result = ctx(words, 3)
    assert "--summary" in result
    assert "--verbose" in result
    assert "-q" not in result
    assert "-v" not in result


def test_complete_options_no_apidef() -> None:
    words = ["papycli", "get", "/pet", ""]
    result = ctx_no_apidef(words, 3)
    assert result == []


def test_complete_options_hides_q_when_no_query_params() -> None:
    # POST /pet はクエリパラメータなし → -q は非表示
    words = ["papycli", "post", "/pet", ""]
    result = ctx(words, 3)
    assert "-q" not in result
    assert "-p" in result
    assert "-d" in result


def test_complete_options_hides_p_when_no_body_params() -> None:
    # GET /pet/findByStatus はボディパラメータなし → -p, -d は非表示
    words = ["papycli", "get", "/pet/findByStatus", ""]
    result = ctx(words, 3)
    assert "-q" in result
    assert "-p" not in result
    assert "-d" not in result


def test_complete_options_shows_all_when_op_unknown() -> None:
    # パスがテンプレートにマッチしない場合はすべてのオプションを表示
    words = ["papycli", "get", "/unknown/path", ""]
    result = ctx(words, 3)
    assert "-q" in result
    assert "-p" in result
    assert "-d" in result


# ---------------------------------------------------------------------------
# パステンプレートマッチング経由の補完
# ---------------------------------------------------------------------------


def test_complete_query_param_via_template() -> None:
    # /pet/99 → /pet/{petId} にマッチ。GET /pet/{petId} はパラメータなし
    words = ["papycli", "get", "/pet/99", "-q", ""]
    result = ctx(words, 4)
    assert result == []


def test_complete_delete_path_param() -> None:
    # DELETE /pet/{petId}
    words = ["papycli", "delete", "/pet/99", ""]
    result = ctx(words, 3)
    # オプション名が候補に出る
    assert "-q" in result or "--summary" in result


# ---------------------------------------------------------------------------
# spec コマンド補完
# ---------------------------------------------------------------------------


def test_complete_spec_resources() -> None:
    result = ctx(["papycli", "spec", ""], 2)
    assert "/pet/findByStatus" in result
    assert "/store/inventory" in result


def test_complete_spec_resource_prefix() -> None:
    result = ctx(["papycli", "spec", "/pet"], 2)
    assert "/pet/findByStatus" in result
    assert "/store/inventory" not in result


def test_complete_spec_includes_full_flag() -> None:
    result = ctx(["papycli", "spec", ""], 2)
    assert "--full" in result


def test_complete_spec_full_flag_prefix() -> None:
    result = ctx(["papycli", "spec", "--f"], 2)
    assert "--full" in result


def test_complete_spec_no_apidef_returns_full_flag() -> None:
    result = ctx_no_apidef(["papycli", "spec", ""], 2)
    assert "--full" in result
    assert len([r for r in result if r != "--full"]) == 0


def test_complete_spec_no_apidef() -> None:
    result = ctx_no_apidef(["papycli", "spec", ""], 2)
    assert "--full" in result


def test_complete_spec_no_further_completion() -> None:
    result = ctx(["papycli", "spec", "/pet", ""], 3)
    assert result == []


def test_complete_spec_full_resource() -> None:
    # spec --full <TAB> → リソースパスが補完される
    result = ctx(["papycli", "spec", "--full", ""], 3)
    assert "/pet" in result
    assert "/pet/findByStatus" in result


def test_complete_spec_full_resource_prefix() -> None:
    # spec --full /pet<TAB> → /pet プレフィックスのパスのみ
    result = ctx(["papycli", "spec", "--full", "/pet"], 3)
    assert "/pet/findByStatus" in result
    assert "/store/inventory" not in result


def test_complete_spec_full_resource_no_apidef() -> None:
    # apidef なしでは補完候補なし
    result = ctx_no_apidef(["papycli", "spec", "--full", ""], 3)
    assert result == []


# ---------------------------------------------------------------------------
# generate_script
# ---------------------------------------------------------------------------


def test_generate_bash_script() -> None:
    script = generate_script("bash")
    assert "_papycli_completion" in script
    assert "complete" in script
    assert "papycli _complete" in script


def test_generate_zsh_script() -> None:
    script = generate_script("zsh")
    assert "_papycli" in script
    assert "compdef" in script
    assert "papycli _complete" in script


# ---------------------------------------------------------------------------
# 使用済みパラメータ名の除外
# ---------------------------------------------------------------------------


def test_used_param_names_single() -> None:
    words = ["papycli", "post", "/pet", "-p", "name", "foo", "-p", ""]
    assert _used_param_names(words, "-p") == {"name"}


def test_used_param_names_multiple() -> None:
    words = ["papycli", "post", "/pet", "-p", "name", "foo", "-p", "status", "available", "-p", ""]
    assert _used_param_names(words, "-p") == {"name", "status"}


def test_used_param_names_empty() -> None:
    words = ["papycli", "post", "/pet", "-p", ""]
    assert _used_param_names(words, "-p") == set()


def test_used_param_names_counts_name_without_value() -> None:
    # -p name (値なし), -p status available, -p <TAB> の状況を再現
    # name は値なしでも使用済みとして扱われ、status も使用済み → 両方除外される
    words = ["papycli", "post", "/pet", "-p", "name", "-p", "status", "available", "-p", ""]
    assert _used_param_names(words, "-p") == {"name", "status"}


def test_used_param_names_does_not_mix_flags() -> None:
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status", "available", "-p", ""]
    assert _used_param_names(words, "-p") == set()
    assert _used_param_names(words, "-q") == {"status"}


def test_complete_body_param_excludes_used() -> None:
    # name を使用済み → 候補に出ないこと
    words = ["papycli", "post", "/pet", "-p", "name", "foo", "-p", ""]
    result = ctx(words, 7)
    assert "name*" not in result
    assert "status" in result
    assert "photoUrls*" in result


def test_complete_body_param_excludes_used_with_asterisk() -> None:
    # 補完で選択した name*（末尾 * あり）が使用済みとして正しく除外されること
    words = ["papycli", "post", "/pet", "-p", "name*", "foo", "-p", ""]
    result = ctx(words, 7)
    assert "name*" not in result
    assert "status" in result
    assert "photoUrls*" in result


def test_complete_body_param_excludes_multiple_used() -> None:
    words = ["papycli", "post", "/pet", "-p", "name", "foo", "-p", "status", "available", "-p", ""]
    result = ctx(words, 10)
    assert "name*" not in result
    assert "status" not in result
    assert "photoUrls*" in result


def test_complete_query_param_excludes_used() -> None:
    # status を使用済み → 候補に出ないこと（findByStatus は status のみなので空リスト）
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status", "available", "-q", ""]
    result = ctx(words, 7)
    assert "status" not in result


def test_complete_query_param_name_not_excluded_while_typing() -> None:
    # -q status<TAB> → status 自身を補完中なので候補に出ること
    words = ["papycli", "get", "/pet/findByStatus", "-q", "status"]
    result = ctx(words, 4)
    assert "status" in result


def test_complete_body_param_name_not_excluded_while_typing() -> None:
    # -p name<TAB> → name 自身を補完中なので候補に出ること
    words = ["papycli", "post", "/pet", "-p", "name"]
    result = ctx(words, 4)
    assert "name*" in result


def test_complete_body_enum_value_with_asterisk_param_name() -> None:
    # 補完で status* が選択された場合（実際は status は任意なので * なしだが、
    # 仮に * 付きで渡された場合でも enum 値を正しく補完できること）
    words = ["papycli", "post", "/pet", "-p", "status*", ""]
    result = ctx(words, 5)
    assert "available" in result
    assert "pending" in result
    assert "sold" in result


def test_generate_bash_has_comp_words() -> None:
    script = generate_script("bash")
    assert "COMP_WORDS" in script
    assert "COMP_CWORD" in script


def test_generate_bash_has_config_add_file_fallback() -> None:
    script = generate_script("bash")
    assert "compgen -f" in script
    assert "compopt -o filenames" in script


def test_generate_bash_config_add_fallback_condition() -> None:
    script = generate_script("bash")
    # config add コンテキストを検出する条件が含まれていること
    assert '"config"' in script
    assert '"add"' in script
    assert "COMP_CWORD" in script


def test_generate_zsh_has_current() -> None:
    script = generate_script("zsh")
    assert "CURRENT" in script


def test_generate_zsh_has_config_add_file_fallback() -> None:
    script = generate_script("zsh")
    assert "_files" in script


def test_generate_zsh_config_add_fallback_condition() -> None:
    script = generate_script("zsh")
    # config add コンテキストを検出する条件文が正確に含まれていること
    assert '"${words[2]}" == "config"' in script
    assert '"${words[3]}" == "add"' in script
    assert "$CURRENT -eq 4" in script


# ---------------------------------------------------------------------------
# generate_script with custom cmd_name
# ---------------------------------------------------------------------------


def test_generate_bash_with_alias_cmd_name() -> None:
    script = generate_script("bash", "petcli")
    assert "_petcli_completion" in script
    assert "complete -o nospace -F _petcli_completion petcli" in script
    assert "petcli _complete" in script


def test_generate_zsh_with_alias_cmd_name() -> None:
    script = generate_script("zsh", "petcli")
    assert "_petcli()" in script
    assert "compdef _petcli petcli" in script
    assert "petcli _complete" in script


def test_generate_bash_hyphenated_cmd_name() -> None:
    """ハイフンを含むコマンド名はシェル関数名でアンダースコアに変換される。"""
    script = generate_script("bash", "my-cli")
    assert "_my_cli_completion" in script
    assert "complete -o nospace -F _my_cli_completion my-cli" in script


def test_generate_zsh_hyphenated_cmd_name() -> None:
    script = generate_script("zsh", "my-cli")
    assert "_my_cli()" in script
    assert "compdef _my_cli my-cli" in script


def test_generate_script_default_is_papycli_bash() -> None:
    assert generate_script("bash") == generate_script("bash", "papycli")


def test_generate_script_default_is_papycli_zsh() -> None:
    assert generate_script("zsh") == generate_script("zsh", "papycli")


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
