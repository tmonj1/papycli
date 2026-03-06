"""CLI エントリポイント."""

import click

from papycli import __version__


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """papycli — OpenAPI 3.0 仕様から REST API を呼び出す CLI ツール."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# サブコマンドはマイルストーンごとに追加する
