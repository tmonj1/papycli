"""CLI entry point."""

import json
import sys
from pathlib import Path

import click
import requests

from papycli import __version__
from papycli.api_call import call_api, match_path_template
from papycli.config import (
    get_apis_dir,
    get_conf_dir,
    get_conf_path,
    load_conf,
    load_current_apidef,
    remove_api,
    save_conf,
    set_default_api,
)
from papycli.completion import generate_script, get_completions
from papycli.i18n import h
from papycli.init_cmd import init_api, register_initialized_api
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
def cmd_config_add(spec_file: str) -> None:
    spec_path = Path(spec_file)
    conf_dir = get_conf_dir()

    if spec_path.stem == "default":
        click.echo("Error: 'default' is a reserved name and cannot be used as an API name.", err=True)
        sys.exit(1)

    try:
        api_name, base_url = init_api(spec_path, conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    conf = load_conf(conf_dir)
    register_initialized_api(conf, api_name, spec_path, base_url)
    save_conf(conf, conf_dir)

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

    if api_name == "default":
        click.echo("Error: 'default' is a reserved configuration key, not an API name.", err=True)
        sys.exit(1)

    registered = [k for k in conf if k != "default" and isinstance(conf[k], dict)]
    if api_name not in conf or not isinstance(conf[api_name], dict):
        if registered:
            click.echo(f"Error: API '{api_name}' is not registered.", err=True)
            click.echo(f"Registered APIs: {', '.join(registered)}", err=True)
        else:
            click.echo("Error: No APIs registered. Run 'papycli config add <spec>' first.", err=True)
        sys.exit(1)

    set_default_api(conf, api_name)
    save_conf(conf, conf_dir)
    click.echo(f"Switched default API to '{api_name}'")


@cmd_config.command(
    "remove",
    help=h("Remove a registered API.", "登録済み API を削除する。"),
)
@click.argument("api_name", metavar="API_NAME")
def cmd_config_remove(api_name: str) -> None:
    conf_dir = get_conf_dir()
    conf = load_conf(conf_dir)

    if api_name == "default":
        click.echo("Error: 'default' is a reserved configuration key, not an API name.", err=True)
        sys.exit(1)

    if api_name not in conf or not isinstance(conf[api_name], dict):
        registered = [k for k in conf if k != "default" and isinstance(conf[k], dict)]
        if registered:
            click.echo(f"Error: API '{api_name}' is not registered.", err=True)
            click.echo(f"Registered APIs: {', '.join(registered)}", err=True)
        else:
            click.echo("Error: No APIs registered. Run 'papycli config add <spec>' first.", err=True)
        sys.exit(1)

    api_entry = conf[api_name]
    prev_default = conf.get("default")
    remove_api(conf, api_name)
    save_conf(conf, conf_dir)

    # apidef ファイルを削除する
    apidef_filename = str(api_entry.get("apidef", f"{api_name}.json"))
    apidef_path = get_apis_dir(conf_dir) / apidef_filename
    if apidef_path.exists():
        apidef_path.unlink()

    click.echo(f"Removed API '{api_name}'")
    if prev_default == api_name:
        new_default = conf.get("default")
        if new_default:
            click.echo(f"  Default API changed to '{new_default}'")
        else:
            click.echo("  No default API set. Run 'papycli config add <spec>' to register one.")


@cmd_config.command(
    "list",
    help=h("List registered APIs and current configuration.", "登録済み API と現在の設定を一覧表示する。"),
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
    click.echo(generate_script(shell), nl=False)


# ---------------------------------------------------------------------------
# summary command
# ---------------------------------------------------------------------------


@cli.command(
    "summary",
    help=h(
        "List available endpoints.\n\nFilter by RESOURCE path prefix if given.",
        "登録済み API のエンドポイント一覧を表示する。\n\nRESOURCE を指定するとそのパスプレフィックスで絞り込む。",
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
# Shell completion
# ---------------------------------------------------------------------------


@cli.command("_complete", hidden=True, context_settings={"ignore_unknown_options": True})
@click.argument("current_index", type=int)
@click.argument("words", nargs=-1, type=click.UNPROCESSED)
def cmd_complete(current_index: int, words: tuple[str, ...]) -> None:
    results = get_completions(list(words), current_index, get_conf_dir())
    if results:
        click.echo("\n".join(results))
