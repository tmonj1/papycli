"""CLI エントリポイント."""

import json
import sys
from pathlib import Path

import click

from papycli import __version__
from papycli.config import (
    get_conf_dir,
    get_conf_path,
    load_conf,
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


# API 呼び出しコマンド (get / post / put / patch / delete) は M3 で追加する
