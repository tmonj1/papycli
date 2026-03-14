# papycli-debug-response-filter

A minimal example of a [papycli](https://github.com/tmonj1/papycli) response filter plugin.

This plugin prints the received `ResponseContext` to **stderr** after each request — useful as a starting point for writing your own filter.

> **Warning:** This plugin is intended for **debugging and development only**.
> It prints response headers without redaction, which may expose sensitive values such as
> Set-Cookie headers or authentication tokens. Do NOT use this plugin in production environments.

## What it does

After every `papycli` API call, it writes to stderr:

```
[papycli-debug-response-filter]
  Method  : GET
  URL     : http://localhost:8080/api/v3/store/inventory
  Status  : 200 OK
  Headers : {"Content-Type": "application/json", ...}
  Body    : {"approved": 1, ...}
```

## Installation

Install papycli and this plugin into the same Python environment:

```bash
pip install papycli
pip install -e /path/to/papycli/examples/response_filter
```

Once installed, the filter is picked up automatically — no additional configuration needed.

## Usage

Run any papycli command. The filter output appears on **stderr**, while the API response is printed to **stdout** as usual:

```bash
papycli get /store/inventory
```

```
# stderr:
[papycli-debug-response-filter]
  Method  : GET
  URL     : http://localhost:8080/api/v3/store/inventory
  Status  : 200 OK
  Headers : {"Content-Type": "application/json; charset=utf-8"}
  Body    : {"approved": 1, "sold": 2}

# stdout:
{
  "approved": 1,
  "sold": 2
}
```

Because debug output goes to stderr, stdout remains machine-readable and piping still works:

```bash
papycli get /store/inventory | jq '.approved'
```

## How it works

The plugin is registered via the `papycli.response_filters` entry point in `pyproject.toml`:

```toml
[project.entry-points."papycli.response_filters"]
debug = "papycli_debug_response_filter:response_filter"
```

papycli discovers all installed plugins in this group, sorts them by name, and calls each one after receiving the response. The filter receives a `ResponseContext` and must return a (possibly modified) `ResponseContext`, or `None` to suppress the response output and stop the filter chain.

## Writing your own filter

1. Copy this directory as a starting point.
2. Edit `src/papycli_debug_response_filter/__init__.py` — inspect or modify `ctx` fields as needed and return it.
3. Change the package name in `pyproject.toml` and re-install with `pip install -e .`.

See the [papycli README](../../README.md#response-filter-plugins) for the full `ResponseContext` field reference.
