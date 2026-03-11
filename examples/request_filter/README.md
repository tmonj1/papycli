# papycli-debug-filter

A minimal example of a [papycli](https://github.com/tmonj1/papycli) request filter plugin.

This plugin prints the outgoing `RequestContext` to **stderr** before each request — useful as a starting point for writing your own filter.

> **Warning:** This plugin is intended for **debugging and development only**.
> It prints request headers without redaction, which may expose sensitive values such as
> Authorization tokens or API keys. Do NOT use this plugin in production environments.

## What it does

Before every `papycli` API call, it writes to stderr:

```
[papycli-debug-filter]
  Method : GET
  URL    : http://localhost:8080/api/v3/store/inventory
  Query  : (none)
  Body   : (none)
  Headers: (none)
```

## Installation

Install papycli and this plugin into the same Python environment:

```bash
pip install papycli
pip install -e /path/to/papycli/examples/request_filter
```

Once installed, the filter is picked up automatically — no additional configuration needed.

## Usage

Run any papycli command. The filter output appears on **stderr**, while the API response is printed to **stdout** as usual:

```bash
papycli get /store/inventory
```

```
# stderr:
[papycli-debug-filter]
  Method : GET
  URL    : http://localhost:8080/api/v3/store/inventory
  Query  : (none)
  Body   : (none)
  Headers: (none)

# stdout:
{
  "approved": 1,
  ...
}
```

Because debug output goes to stderr, stdout remains machine-readable and piping still works:

```bash
papycli get /store/inventory | jq '.approved'
```

## How it works

The plugin is registered via the `papycli.request_filters` entry point in `pyproject.toml`:

```toml
[project.entry-points."papycli.request_filters"]
debug = "papycli_debug_filter:request_filter"
```

papycli discovers all installed plugins in this group, sorts them by name, and calls each one before sending the request. The filter receives a `RequestContext` and must return a (possibly modified) `RequestContext`.

## Writing your own filter

1. Copy this directory as a starting point.
2. Edit `src/papycli_debug_filter/__init__.py` — modify `ctx` fields as needed and return it.
3. Change the package name in `pyproject.toml` and re-install with `pip install -e .`.

See the [papycli README](../../README.md#request-filter-plugins) for the full `RequestContext` field reference.
