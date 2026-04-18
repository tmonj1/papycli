"""CLI entry point."""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

import click
import requests
from dotenv import load_dotenv

from papycli import __version__
from papycli.api_call import call_api, match_path_template
from papycli.checker import check_request
from papycli.completion import _SAFE_CMD_RE, generate_static_script, get_completions
from papycli.config import (
    get_aliases,
    get_apis_dir,
    get_conf_dir,
    get_conf_path,
    get_logfile,
    load_conf,
    load_current_apidef,
    load_current_raw_spec,
    remove_alias,
    remove_api,
    save_conf,
    set_alias,
    set_api_override,
    set_default_api,
    set_logfile,
    unset_logfile,
)
from papycli.i18n import h
from papycli.init_cmd import init_api, register_initialized_api
from papycli.spec_loader import collect_schema_refs
from papycli.summary import format_endpoint_detail, format_summary_csv, print_summary


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=h(
        "papycli — Call REST APIs defined in OpenAPI 3.0 specs.",
        "papycli — OpenAPI 3.0 仕様から REST API を呼び出す CLI ツール.",
    ),
)
@click.version_option(__version__, "-V", "--version")
@click.pass_context
def cli(ctx: click.Context) -> None:
    # 毎回リセットしてからエイリアス検出する（繰り返し呼び出し時のグローバル汚染を防ぐ）
    set_api_override(None)
    # ctx.info_name は CliRunner/実シェルいずれでも正確な呼び出しコマンド名を返す
    # .stem で Windows の ".exe" 等を除去する
    cmd_name = Path(ctx.info_name or "").stem
    if cmd_name != "papycli":
        try:
            _conf = load_conf(get_conf_dir())
            _aliases = get_aliases(_conf)
            if cmd_name in _aliases:
                set_api_override(_aliases[cmd_name])
        except Exception as e:
            click.echo(f"Warning: alias detection failed: {e}", err=True)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# config subgroup
# ---------------------------------------------------------------------------


@cli.group(
    "config",
    invoke_without_command=True,
    help=h("Manage API configurations.", "API 設定を管理する。"),
)
@click.pass_context
def cmd_config(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cmd_config.command(
    "add",
    help=h(
        "Register an API from an OpenAPI spec file.",
        "OpenAPI spec ファイルから API を登録する。",
    ),
)
@click.argument("spec_file", metavar="SPEC_FILE", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--upgrade", "upgrade", is_flag=True,
    help=h(
        "Update an existing registered API with a new spec."
        " If the API is not registered yet, register it as new.",
        "既存の登録済み API を新しい spec で更新する。未登録の場合は新規登録として処理する。",
    ),
)
def cmd_config_add(spec_file: str, upgrade: bool) -> None:
    spec_path = Path(spec_file)
    conf_dir = get_conf_dir()

    if spec_path.stem in ("default", "aliases", "logfile"):
        click.echo(
            f"Error: '{spec_path.stem}' is a reserved name and cannot be used as an API name.",
            err=True,
        )
        sys.exit(1)

    conf = load_conf(conf_dir)
    api_name = spec_path.stem
    already_registered = api_name in conf and isinstance(conf[api_name], dict)

    if not upgrade and already_registered:
        click.echo(
            f"Error: API '{api_name}' is already registered. Use --upgrade to update it.",
            err=True,
        )
        sys.exit(1)

    # save_conf() が失敗したときに apis/ 配下の apidef/raw spec ファイルと
    # config の不整合が発生しないよう、旧状態を常に記録しておく。
    # existing: 上書き前の内容 (bytes)、None: 上書き前に存在しなかった（削除対象）
    apis_dir = get_apis_dir(conf_dir)
    file_snapshot: dict[Path, bytes | None] = {}
    for p in [apis_dir / f"{api_name}.json", apis_dir / f"{api_name}.spec.json"]:
        file_snapshot[p] = p.read_bytes() if p.exists() else None

    try:
        api_name, base_url = init_api(spec_path, conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    register_initialized_api(conf, api_name, spec_path, base_url)
    try:
        save_conf(conf, conf_dir)
    except Exception as e:
        rollback_errors: list[str] = []
        for p, data in file_snapshot.items():
            try:
                if data is None:
                    p.unlink(missing_ok=True)
                else:
                    p.write_bytes(data)
            except OSError as re:
                rollback_errors.append(f"{p}: {re}")
        click.echo(f"Error: failed to save configuration: {e}", err=True)
        if rollback_errors:
            click.echo(
                "Error: failed to rollback updated API files; manual cleanup may be required:",
                err=True,
            )
            for msg in rollback_errors:
                click.echo(f"  {msg}", err=True)
        sys.exit(1)

    if upgrade and already_registered:
        click.echo(f"Updated API '{api_name}'")
    else:
        click.echo(f"Registered API '{api_name}'")
    if base_url:
        click.echo(f"  Base URL : {base_url}")
    else:
        click.echo("  Base URL : (not set — edit papycli.conf to add url)")
    click.echo(f"  Conf dir : {conf_dir}")


@cmd_config.command(
    "use",
    help=h("Switch the active API.", "アクティブな API を切り替える。"),
)
@click.argument("api_name", metavar="API_NAME")
def cmd_config_use(api_name: str) -> None:
    conf_dir = get_conf_dir()
    conf = load_conf(conf_dir)

    if api_name in ("default", "aliases"):
        click.echo(
            f"Error: '{api_name}' is a reserved configuration key, not an API name.", err=True
        )
        sys.exit(1)

    registered = [k for k in conf if k not in ("default", "aliases") and isinstance(conf[k], dict)]
    if api_name not in conf or not isinstance(conf[api_name], dict):
        if registered:
            click.echo(f"Error: API '{api_name}' is not registered.", err=True)
            click.echo(f"Registered APIs: {', '.join(registered)}", err=True)
        else:
            click.echo(
                "Error: No APIs registered. Run 'papycli config add <spec>' first.", err=True
            )
        sys.exit(1)

    set_default_api(conf, api_name)
    save_conf(conf, conf_dir)
    click.echo(f"Switched default API to '{api_name}'")

    # シェル補完の再登録ヒントを表示する
    shell = os.environ.get("SHELL", "")
    raw_name = Path(click.get_current_context().find_root().info_name or "").stem
    cmd_name = raw_name if _SAFE_CMD_RE.match(raw_name) else "papycli"
    if shell.endswith("zsh"):
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script zsh)"'
        )
    elif shell.endswith("bash"):
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script bash)"'
        )
    else:
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script bash)"'
            f"  # bash"
        )
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script zsh)"'
            f"   # zsh"
        )


@cmd_config.command(
    "remove",
    help=h("Remove a registered API.", "登録済み API を削除する。"),
)
@click.argument("api_name", metavar="API_NAME")
def cmd_config_remove(api_name: str) -> None:
    conf_dir = get_conf_dir()
    conf = load_conf(conf_dir)

    if api_name in ("default", "aliases"):
        click.echo(
            f"Error: '{api_name}' is a reserved configuration key, not an API name.", err=True
        )
        sys.exit(1)

    if api_name not in conf or not isinstance(conf[api_name], dict):
        registered = [
            k for k in conf if k not in ("default", "aliases") and isinstance(conf[k], dict)
        ]
        if registered:
            click.echo(f"Error: API '{api_name}' is not registered.", err=True)
            click.echo(f"Registered APIs: {', '.join(registered)}", err=True)
        else:
            click.echo(
                "Error: No APIs registered. Run 'papycli config add <spec>' first.", err=True
            )
        sys.exit(1)

    api_entry = conf[api_name]
    prev_default = conf.get("default")
    remove_api(conf, api_name)
    save_conf(conf, conf_dir)

    # apidef ファイルと raw spec ファイルを削除する
    apidef_filename = str(api_entry.get("apidef", f"{api_name}.json"))
    apidef_path = get_apis_dir(conf_dir) / apidef_filename
    if apidef_path.exists():
        apidef_path.unlink()
    spec_path = get_apis_dir(conf_dir) / f"{api_name}.spec.json"
    if spec_path.exists():
        spec_path.unlink()

    click.echo(f"Removed API '{api_name}'")
    if prev_default == api_name:
        new_default = conf.get("default")
        if new_default:
            click.echo(f"  Default API changed to '{new_default}'")
        else:
            click.echo("  No default API set. Run 'papycli config add <spec>' to register one.")


@cmd_config.command(
    "list",
    help=h(
        "List registered APIs and current configuration.",
        "登録済み API と現在の設定を一覧表示する。",
    ),
)
def cmd_config_list() -> None:
    conf_dir = get_conf_dir()
    conf_path = get_conf_path(conf_dir)

    click.echo(f"Conf dir  : {conf_dir}")
    click.echo(f"Conf file : {conf_path}")
    click.echo("")

    conf = load_conf(conf_dir)
    if not conf:
        click.echo("(no configuration — run 'papycli config add <spec>' to get started)")
        return

    click.echo(json.dumps(conf, indent=2, ensure_ascii=False))


@cmd_config.command(
    "log",
    help=h(
        "View or set the log file path.\n\n"
        "Run without arguments to show the current path.\n"
        "Pass PATH to set a new log file.\n"
        "Use --unset to disable logging.",
        "ログファイルのパスを表示・設定する。\n\n"
        "引数なしで現在のパスを表示。PATH を指定するとログファイルを設定。\n"
        "--unset でログを無効化する。",
    ),
)
@click.argument("path", required=False, default=None)
@click.option(
    "--unset", is_flag=True,
    help=h(
        "Remove the log file setting (disable logging).",
        "ログファイル設定を削除する（ログ無効化）。",
    ),
)
def cmd_config_log(path: str | None, unset: bool) -> None:
    if unset and path is not None:
        click.echo("Error: --unset and PATH cannot be used together.", err=True)
        sys.exit(1)

    conf_dir = get_conf_dir()
    try:
        conf = load_conf(conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if unset:
        unset_logfile(conf)
        try:
            save_conf(conf, conf_dir)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        click.echo("Log file setting removed.")
        return

    if path is not None:
        set_logfile(conf, path)
        try:
            save_conf(conf, conf_dir)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        click.echo(f"Log file set to: {path}")
        return

    logfile = get_logfile(conf)
    if logfile:
        click.echo(f"Log file: {logfile}")
    else:
        click.echo("Log file: (not set)")


@cmd_config.command(
    "completion-script",
    help=h(
        'Print a shell completion script.\n\n'
        'Usage (bash): eval "$(papycli config completion-script bash)"\n\n'
        'Usage (zsh):  eval "$(papycli config completion-script zsh)"',
        'シェル補完スクリプトを出力する。\n\n'
        '使い方 (bash): eval "$(papycli config completion-script bash)"\n\n'
        '使い方 (zsh):  eval "$(papycli config completion-script zsh)"',
    ),
)
@click.argument("shell", type=click.Choice(["bash", "zsh"]))
def cmd_config_completion_script(shell: str) -> None:
    # find_root().info_name でエイリアス経由でも正確なコマンド名を取得する
    root_name = click.get_current_context().find_root().info_name or ""
    cmd_name = Path(root_name).stem  # .stem で Windows の ".exe" 等を除去する
    conf_dir = get_conf_dir()
    api_names: list[str] = []
    apidef = None
    conf: dict[str, Any] | None = None
    try:
        conf = load_conf(conf_dir)
        api_names = [
            k for k in conf if k not in ("default", "aliases") and isinstance(conf[k], dict)
        ]
    except Exception as e:
        click.echo(f"Warning: failed to load configuration for completion: {e}", err=True)
    # デフォルト API が設定されている場合のみ apidef を読み込む。
    # 未設定・設定ファイル未作成は通常ケースのため警告なしでスキップする。
    if conf is not None and isinstance(conf.get("default"), str) and conf.get("default"):
        try:
            apidef, _ = load_current_apidef(conf_dir, conf=conf)
        except Exception as e:
            click.echo(
                f"Warning: failed to load current API definition for completion: {e}", err=True
            )
    try:
        click.echo(generate_static_script(shell, cmd_name, apidef, api_names), nl=False)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cmd_config.command(
    "alias",
    help=h(
        "Create, list, or delete command aliases.\n\n"
        "ALIAS_NAME: the new command name (e.g. 'petcli').\n"
        "SPEC_NAME: registered API spec name (defaults to current default).\n\n"
        "Omit both arguments to list configured aliases.\n"
        "Use -d ALIAS_NAME to delete an alias.",
        "コマンドエイリアスの作成・一覧・削除を行う。\n\n"
        "ALIAS_NAME: 新しいコマンド名（例: 'petcli'）。\n"
        "SPEC_NAME: 登録済みスペック名（省略時は現在のデフォルト）。\n\n"
        "両引数を省略するとエイリアス一覧を表示する。\n"
        "-d ALIAS_NAME でエイリアスを削除する。",
    ),
)
@click.argument("alias_name", required=False, default=None)
@click.argument("spec_name", required=False, default=None)
@click.option(
    "-d", "delete", is_flag=True,
    help=h("Delete the specified alias.", "指定したエイリアスを削除する。"),
)
def cmd_config_alias(
    alias_name: str | None,
    spec_name: str | None,
    delete: bool,
) -> None:
    conf_dir = get_conf_dir()
    conf = load_conf(conf_dir)

    # alias_name が指定されている場合は安全な名前かチェックする
    if alias_name is not None and not _SAFE_CMD_RE.match(alias_name):
        click.echo(
            f"Error: alias name '{alias_name}' is invalid. "
            "Must start with a letter or digit, and contain only"
            " letters, digits, hyphens, and underscores.",
            err=True,
        )
        sys.exit(1)

    # -d: エイリアスを削除する
    if delete:
        if alias_name is None:
            click.echo("Error: alias name is required with -d.", err=True)
            sys.exit(1)
        if spec_name is not None:
            click.echo("Error: SPEC_NAME cannot be specified with -d.", err=True)
            sys.exit(1)
        raw_aliases = conf.get("aliases")
        if not isinstance(raw_aliases, dict) or alias_name not in raw_aliases:
            click.echo(f"Error: alias '{alias_name}' not found.", err=True)
            sys.exit(1)
        # symlink を先に削除し、失敗時は config を変更せずに終了する
        symlink = conf_dir / "bin" / alias_name
        if symlink.is_symlink():
            try:
                symlink.unlink()
            except OSError as e:
                click.echo(f"Error: failed to remove symlink: {e}", err=True)
                sys.exit(1)
        elif symlink.exists():
            click.echo(
                f"Error: '{symlink}' is not a symlink created by papycli. "
                "Remove it manually before deleting the alias.",
                err=True,
            )
            sys.exit(1)
        remove_alias(conf, alias_name)
        save_conf(conf, conf_dir)
        click.echo(f"Alias '{alias_name}' removed.")
        return

    # 引数なし: エイリアス一覧を表示する
    if alias_name is None:
        aliases = get_aliases(conf)
        if not aliases:
            click.echo("(no aliases configured)")
        else:
            for name, spec in aliases.items():
                click.echo(f"{name} -> {spec}")
        return

    # SPEC_NAME 省略時は config の default を使用する。
    # エイリアス呼び出し時のオーバーライドを避けるため get_default_api は使わず
    # config dict を直接参照する。
    if spec_name is None:
        raw_default = conf.get("default")
        if not isinstance(raw_default, str) or not raw_default:
            click.echo(
                "Error: no SPEC_NAME given and no default API configured.", err=True
            )
            sys.exit(1)
        spec_name = raw_default

    # スペックが登録済みかチェックする（予約済みキーは除外）
    _reserved = ("default", "aliases")
    if spec_name in _reserved or not isinstance(conf.get(spec_name), dict):
        click.echo(f"Error: spec '{spec_name}' is not registered.", err=True)
        sys.exit(1)

    # papycli 実行ファイルのパスを解決する。
    # エイリアス経由で呼び出された場合（例: petcli config alias ...）は "papycli" が
    # PATH に直接なくても、現在のコマンド名で再試行してシンボリックリンクを辿る。
    root_info_name = click.get_current_context().find_root().info_name or ""
    papycli_path = shutil.which("papycli") or shutil.which(Path(root_info_name).stem)
    if papycli_path is None:
        click.echo(
            "Error: cannot locate the papycli executable in PATH. "
            "Ensure papycli is installed and available on your PATH.",
            err=True,
        )
        sys.exit(1)
    papycli_exe = Path(papycli_path).resolve()
    if papycli_exe.stem != "papycli":
        click.echo(
            f"Error: resolved executable '{papycli_exe}' does not appear to be papycli. "
            "Ensure 'papycli' is available on your PATH.",
            err=True,
        )
        sys.exit(1)

    # ~/.papycli/bin/<alias_name> -> papycli 実行ファイルへの symlink を先に作成する。
    # 失敗した場合は config を変更せずにエラー終了する。
    bin_dir = conf_dir / "bin"
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        symlink = bin_dir / alias_name
        if symlink.is_symlink():
            symlink.unlink()
        elif symlink.exists():
            click.echo(
                f"Error: '{symlink}' already exists and is not a symlink. "
                "Remove it manually to create the alias.",
                err=True,
            )
            sys.exit(1)
        symlink.symlink_to(papycli_exe)
    except OSError as e:
        msg = f"Error: failed to create symlink: {e}"
        if sys.platform == "win32":
            msg += (
                "\nOn Windows, symlink creation requires either Developer Mode "
                "(Settings → For developers → Developer Mode) or running as Administrator. "
                "Note: even with symlinks enabled, extensionless commands are not resolved "
                "by default on Windows (PATHEXT does not include entries without extensions). "
                "Consider using WSL or Git Bash for alias functionality."
            )
        click.echo(msg, err=True)
        sys.exit(1)

    # symlink 作成後に config を保存する（失敗時は symlink を rollback する）
    # OSError 以外（json.dump の TypeError/ValueError 等）も捕捉して一貫性を保つ
    try:
        set_alias(conf, alias_name, spec_name)
        save_conf(conf, conf_dir)
    except Exception as e:
        symlink.unlink(missing_ok=True)
        click.echo(f"Error: failed to save config: {e}", err=True)
        sys.exit(1)

    click.echo(f"Alias '{alias_name}' -> '{spec_name}' created.")
    click.echo(f"Symlink: {symlink} -> {papycli_exe}")
    click.echo("\nAdd the following to your shell profile if not already set:")
    click.echo(f'  export PATH="{bin_dir}:$PATH"')
    click.echo(f"\nEnable shell completion for '{alias_name}':")
    click.echo(f'  eval "$({alias_name} config completion-script bash)"  # bash')
    click.echo(f'  eval "$({alias_name} config completion-script zsh)"   # zsh')


# ---------------------------------------------------------------------------
# summary command
# ---------------------------------------------------------------------------


@cli.command(
    "summary",
    help=h(
        "List available endpoints.\n\nFilter by RESOURCE path prefix if given.",
        "登録済み API のエンドポイント一覧を表示する。\n\n"
        "RESOURCE を指定するとそのパスプレフィックスで絞り込む。",
    ),
)
@click.argument("resource", required=False, default=None)
@click.option(
    "--csv", "as_csv", is_flag=True,
    help=h("Output in CSV format.", "CSV フォーマットで出力する。"),
)
def cmd_summary(resource: str | None, as_csv: bool) -> None:
    conf_dir = get_conf_dir()
    try:
        apidef, _ = load_current_apidef(conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if as_csv:
        click.echo(format_summary_csv(apidef), nl=False)
    else:
        print_summary(apidef, resource_filter=resource)


# ---------------------------------------------------------------------------
# spec command
# ---------------------------------------------------------------------------


@cli.command(
    "spec",
    help=h(
        "Show request spec (path, method, query/body parameters) for each endpoint.\n\n"
        "Filter by RESOURCE path if given.\n\n"
        "Use --full to output the OpenAPI spec (including response definitions).\n"
        "With RESOURCE, outputs only the matching path entry and referenced schemas.",
        "各エンドポイントのリクエスト仕様（パス・メソッド・クエリ/ボディパラメータ）を表示する。\n\n"
        "RESOURCE を指定するとそのパスのエントリのみ表示する。\n\n"
        "--full を指定するとレスポンス定義を含む OpenAPI spec を出力する。\n"
        "RESOURCE と組み合わせると該当パスのエントリと参照スキーマのみを出力する。",
    ),
)
@click.argument("resource", required=False, default=None)
@click.option("--full", is_flag=True, default=False, help=h(
    "Output the OpenAPI spec (JSON). With RESOURCE, outputs only"
    " the matching path entry and referenced schemas.",
    "OpenAPI spec を JSON 形式で出力する。RESOURCE を指定すると"
    "該当パスのエントリと参照スキーマのみを出力する。",
))
def cmd_spec(resource: str | None, full: bool) -> None:
    conf_dir = get_conf_dir()

    if full:
        try:
            raw_spec = load_current_raw_spec(conf_dir)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        if resource is not None:
            paths = raw_spec.get("paths", {})
            match = match_path_template(resource, list(paths.keys()))
            if match is None:
                click.echo(f"Error: No matching path for '{resource}'", err=True)
                sys.exit(1)
            template, _ = match
            path_entry = paths[template]
            output: dict[str, Any] = {template: path_entry}
            ref_schemas = collect_schema_refs(path_entry, raw_spec)
            if ref_schemas:
                output["components"] = {"schemas": ref_schemas}
            click.echo(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            click.echo(json.dumps(raw_spec, indent=2, ensure_ascii=False))
        return

    try:
        apidef, _ = load_current_apidef(conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if resource is None:
        click.echo(json.dumps(apidef, indent=2, ensure_ascii=False))
        return

    match = match_path_template(resource, list(apidef.keys()))
    if match is None:
        click.echo(f"Error: No matching path for '{resource}'", err=True)
        sys.exit(1)

    template, _ = match
    click.echo(json.dumps({template: apidef[template]}, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# API call commands (get / post / put / patch / delete)
# ---------------------------------------------------------------------------


def _print_response(resp: requests.Response, *, verbose: bool = False) -> None:
    status_line = f"HTTP {resp.status_code} {resp.reason}"
    if verbose:
        click.echo(status_line)
    elif not resp.ok or not resp.content:
        click.echo(status_line, err=True)
    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            click.echo(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            return
        except ValueError:
            pass
    if resp.text:
        click.echo(resp.text)


def _api_command(method: str) -> click.Command:
    @click.command(
        method,
        help=h(
            f"Send an HTTP {method.upper()} request.",
            f"HTTP {method.upper()} リクエストを送信する。",
        ),
    )
    @click.argument("resource")
    @click.option(
        "-q", "query_params", multiple=True, nargs=2, metavar="NAME VALUE",
        help=h("Query parameter (repeatable).", "クエリパラメータ（繰り返し可）。"),
    )
    @click.option(
        "-p", "body_params", multiple=True, nargs=2, metavar="NAME VALUE",
        help=h("Body parameter (repeatable).", "ボディパラメータ（繰り返し可）。"),
    )
    @click.option(
        "-d", "raw_body", default=None, metavar="JSON",
        help=h("Raw JSON body (overrides -p).", "生の JSON ボディ（-p を上書き）。"),
    )
    @click.option(
        "-H", "extra_headers", multiple=True, metavar="HEADER: VALUE",
        help=h("Custom HTTP header (repeatable).", "カスタム HTTP ヘッダー（繰り返し可）。"),
    )
    @click.option(
        "--summary", "show_summary", is_flag=True,
        help=h(
            "Show endpoint info without sending a request.",
            "リクエストを送らずにエンドポイント情報を表示する。",
        ),
    )
    @click.option(
        "-v", "--verbose", is_flag=True,
        help=h("Show HTTP status line.", "HTTP ステータス行を表示する。"),
    )
    @click.option(
        "--check", "do_check", is_flag=True,
        help=h(
            "Validate params before sending (warn on stderr, request is still sent).",
            "送信前にパラメータを検証する（警告を stderr に出力、リクエストは送信）。",
        ),
    )
    @click.option(
        "--check-strict", "do_check_strict", is_flag=True,
        help=h(
            "Validate params before sending (warn on stderr, abort on failure with exit 1).",
            "送信前にパラメータを検証する（警告を stderr に出力、"
            "問題があればリクエスト中止・exit 1）。",
        ),
    )
    @click.option(
        "--response-check", "do_response_check", is_flag=True,
        help=h(
            "Validate the response body against the OpenAPI schema (warn on stderr).",
            "レスポンスボディを OpenAPI スキーマに照合して検証する（警告を stderr に出力）。",
        ),
    )
    def _cmd(
        resource: str,
        query_params: tuple[tuple[str, str], ...],
        body_params: tuple[tuple[str, str], ...],
        raw_body: str | None,
        extra_headers: tuple[str, ...],
        show_summary: bool,
        verbose: bool,
        do_check: bool,
        do_check_strict: bool,
        do_response_check: bool,
    ) -> None:
        if do_check and do_check_strict:
            click.echo("Error: --check and --check-strict cannot be used together.", err=True)
            sys.exit(1)

        # 補完で選択された際に末尾に * が付いたパラメータ名（例: "name*"）を正規化する。
        query_params = tuple((n.removesuffix("*"), v) for n, v in query_params)
        body_params = tuple((n.removesuffix("*"), v) for n, v in body_params)

        # リソースに "?" が含まれる場合、クエリ文字列を分離してクエリパラメータに追加する。
        # 例: /pet/findByStatus?status=available
        #   → resource=/pet/findByStatus,
        #     query_params=(("status", "available"),) + query_params
        if "?" in resource:
            resource, _, inline_qs = resource.partition("?")
            inline_params = tuple(parse_qsl(inline_qs, keep_blank_values=True))
            query_params = inline_params + query_params

        conf_dir = get_conf_dir()
        try:
            conf = load_conf(conf_dir)
            apidef, base_url = load_current_apidef(conf_dir, conf=conf)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        logfile = get_logfile(conf)

        if show_summary:
            match = match_path_template(resource, list(apidef.keys()))
            if match is None:
                click.echo(f"Error: No matching path for '{resource}'", err=True)
                sys.exit(1)
            template, _ = match
            click.echo(format_endpoint_detail(apidef, method, template))
            return

        raw_spec: dict[str, Any] | None = None
        if do_response_check:
            try:
                raw_spec = load_current_raw_spec(conf_dir, conf=conf)
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)

        if do_check or do_check_strict:
            warnings = check_request(
                apidef, method, resource, query_params, body_params, raw_body
            )
            for warning in warnings:
                click.echo(warning, err=True)
            if do_check_strict and warnings:
                sys.exit(1)

        try:
            resp = call_api(
                method, resource, base_url, apidef,
                query_params=query_params,
                body_params=body_params,
                raw_body=raw_body,
                extra_headers=extra_headers,
                logfile=logfile,
                raw_spec=raw_spec,
                do_response_check=do_response_check,
            )
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        if resp is not None:
            _print_response(resp, verbose=verbose)

    return _cmd


for _method in ("get", "post", "put", "patch", "delete"):
    cli.add_command(_api_command(_method))


# ---------------------------------------------------------------------------
# Shell completion
# ---------------------------------------------------------------------------


@cli.command("_complete", hidden=True, context_settings={"ignore_unknown_options": True})
@click.argument("current_index", type=int)
@click.argument("words", nargs=-1, type=click.UNPROCESSED)
def cmd_complete(current_index: int, words: tuple[str, ...]) -> None:
    results = get_completions(list(words), current_index, get_conf_dir())
    if results:
        stdout_bin = click.get_binary_stream("stdout")
        encoding = sys.stdout.encoding or "utf-8"
        stdout_bin.write(("\n".join(results) + "\n").encode(encoding, errors="replace"))


def _load_env_files() -> None:
    """Load .env files from CWD and PAPYCLI_CONF_DIR (shell env takes precedence).

    Skipped when PAPYCLI_DISABLE_DOTENV=1.
    """
    if os.environ.get("PAPYCLI_DISABLE_DOTENV") == "1":
        return
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    load_dotenv(dotenv_path=get_conf_dir() / ".env", override=False)


def main() -> None:
    """Entry point wrapper: load .env files before invoking CLI."""
    _load_env_files()
    cli()
