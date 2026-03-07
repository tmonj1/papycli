"""CLI エントリポイント."""

import json
import sys
from pathlib import Path

import click
import requests

from papycli import __version__
from papycli.api_call import call_api, match_path_template
from papycli.config import (
    get_conf_dir,
    get_conf_path,
    load_conf,
    load_current_apidef,
    save_conf,
    set_default_api,
)
from papycli.completion import generate_script, get_completions
from papycli.init_cmd import init_api, register_initialized_api
from papycli.summary import format_endpoint_detail, format_summary_csv, print_summary


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """papycli — OpenAPI 3.0 仕様から REST API を呼び出す CLI ツール."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# 設定系コマンド
# ---------------------------------------------------------------------------


@cli.command("init")
@click.argument("spec_file", metavar="SPEC_FILE", type=click.Path(exists=True, dir_okay=False))
def cmd_init(spec_file: str) -> None:
    """OpenAPI spec ファイルから API を初期化する。"""
    spec_path = Path(spec_file)
    conf_dir = get_conf_dir()

    try:
        api_name, base_url = init_api(spec_path, conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    conf = load_conf(conf_dir)
    register_initialized_api(conf, api_name, spec_path, base_url)
    save_conf(conf, conf_dir)

    click.echo(f"Initialized API '{api_name}'")
    if base_url:
        click.echo(f"  Base URL : {base_url}")
    else:
        click.echo("  Base URL : (not set — edit papycli.conf to add url)")
    click.echo(f"  Conf dir : {conf_dir}")


@cli.command("use")
@click.argument("api_name", metavar="API_NAME")
def cmd_use(api_name: str) -> None:
    """アクティブな API を切り替える。"""
    conf_dir = get_conf_dir()
    conf = load_conf(conf_dir)

    if api_name not in conf:
        registered = [k for k in conf if k != "default"]
        if registered:
            click.echo(f"Error: API '{api_name}' is not registered.", err=True)
            click.echo(f"Registered APIs: {', '.join(registered)}", err=True)
        else:
            click.echo("Error: No APIs registered. Run 'papycli init <spec>' first.", err=True)
        sys.exit(1)

    set_default_api(conf, api_name)
    save_conf(conf, conf_dir)
    click.echo(f"Switched default API to '{api_name}'")


@cli.command("conf")
def cmd_conf() -> None:
    """現在の設定と環境変数を表示する。"""
    conf_dir = get_conf_dir()
    conf_path = get_conf_path(conf_dir)

    click.echo(f"Conf dir  : {conf_dir}")
    click.echo(f"Conf file : {conf_path}")
    click.echo("")

    conf = load_conf(conf_dir)
    if not conf:
        click.echo("(no configuration — run 'papycli init <spec>' to get started)")
        return

    click.echo(json.dumps(conf, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# summary コマンド
# ---------------------------------------------------------------------------


@cli.command("summary")
@click.argument("resource", required=False, default=None)
@click.option("--csv", "as_csv", is_flag=True, help="CSV フォーマットで出力する")
def cmd_summary(resource: str | None, as_csv: bool) -> None:
    """登録済み API のエンドポイント一覧を表示する。

    RESOURCE を指定するとそのパスプレフィックスで絞り込む。
    """
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
# API 呼び出しコマンド (get / post / put / patch / delete)
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
    """HTTP メソッドごとの CLI コマンドを生成する。"""

    @click.command(method, help=f"HTTP {method.upper()} リクエストを送信する。")
    @click.argument("resource")
    @click.option("-q", "query_params", multiple=True, nargs=2, metavar="NAME VALUE",
                  help="クエリパラメータ（繰り返し可）")
    @click.option("-p", "body_params", multiple=True, nargs=2, metavar="NAME VALUE",
                  help="ボディパラメータ（繰り返し可）")
    @click.option("-d", "raw_body", default=None, metavar="JSON",
                  help="生の JSON ボディ（-p を上書き）")
    @click.option("-H", "extra_headers", multiple=True, metavar="HEADER: VALUE",
                  help="カスタム HTTP ヘッダー（繰り返し可）")
    @click.option("--summary", "show_summary", is_flag=True,
                  help="リクエストを送らずにエンドポイント情報を表示する")
    @click.option("-v", "--verbose", is_flag=True,
                  help="HTTP ステータス行を表示する")
    def _cmd(
        resource: str,
        query_params: tuple[tuple[str, str], ...],
        body_params: tuple[tuple[str, str], ...],
        raw_body: str | None,
        extra_headers: tuple[str, ...],
        show_summary: bool,
        verbose: bool,
    ) -> None:
        conf_dir = get_conf_dir()
        try:
            apidef, base_url = load_current_apidef(conf_dir)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        if show_summary:
            match = match_path_template(resource, list(apidef.keys()))
            if match is None:
                click.echo(f"Error: No matching path for '{resource}'", err=True)
                sys.exit(1)
            template, _ = match
            click.echo(format_endpoint_detail(apidef, method, template))
            return

        try:
            resp = call_api(
                method, resource, base_url, apidef,
                query_params=query_params,
                body_params=body_params,
                raw_body=raw_body,
                extra_headers=extra_headers,
            )
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        _print_response(resp, verbose=verbose)

    return _cmd


for _method in ("get", "post", "put", "patch", "delete"):
    cli.add_command(_api_command(_method))


# ---------------------------------------------------------------------------
# シェル補完コマンド
# ---------------------------------------------------------------------------


@cli.command("completion-script")
@click.argument("shell", type=click.Choice(["bash", "zsh"]))
def cmd_completion_script(shell: str) -> None:
    """シェル補完スクリプトを出力する。

    使い方 (bash): eval "$(papycli completion-script bash)"

    使い方 (zsh):  eval "$(papycli completion-script zsh)"
    """
    click.echo(generate_script(shell), nl=False)


@cli.command("_complete", hidden=True, context_settings={"ignore_unknown_options": True})
@click.argument("current_index", type=int)
@click.argument("words", nargs=-1, type=click.UNPROCESSED)
def cmd_complete(current_index: int, words: tuple[str, ...]) -> None:
    """シェル補完スクリプトから呼ばれる内部コマンド。補完候補を 1 行 1 候補で出力する。"""
    results = get_completions(list(words), current_index, get_conf_dir())
    if results:
        click.echo("\n".join(results))
