"""CLI エントリポイント."""

import json
import sys
from pathlib import Path

import click
import requests

from papycli import __version__
from papycli.api_call import call_api
from papycli.config import (
    get_conf_dir,
    get_conf_path,
    load_conf,
    load_current_apidef,
    save_conf,
    set_default_api,
)
from papycli.init_cmd import init_api, register_initialized_api


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
# API 呼び出しコマンド (get / post / put / patch / delete)
# ---------------------------------------------------------------------------


def _print_response(resp: "requests.Response") -> None:
    click.echo(f"HTTP {resp.status_code} {resp.reason}")
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
    def _cmd(
        resource: str,
        query_params: tuple[tuple[str, str], ...],
        body_params: tuple[tuple[str, str], ...],
        raw_body: str | None,
        extra_headers: tuple[str, ...],
    ) -> None:
        conf_dir = get_conf_dir()
        try:
            apidef, base_url = load_current_apidef(conf_dir)
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

        _print_response(resp)

    return _cmd


for _method in ("get", "post", "put", "patch", "delete"):
    cli.add_command(_api_command(_method))
