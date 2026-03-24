# papycli — Python CLI for OpenAPI 3.0 REST APIs

`papycli` is an interactive CLI that reads OpenAPI 3.0 specs and lets you call REST API endpoints directly from the terminal.

## Features

- Auto-generates a CLI from any OpenAPI 3.0 spec
- Shell completion for bash and zsh
- Register and switch between multiple APIs
- Inspect API specs with `papycli spec`
- Validate request parameters before sending with `--check` / `--check-strict`
- Validate response body and status code against the OpenAPI spec with `--response-check`
- Automatically coerces `-p` values to the correct JSON type (integer, number, boolean) based on the API spec
- Log requests and responses to a file with `papycli config log`
- Extend request processing with request filter plugins (`papycli.request_filters` entry point)
- Inspect and transform responses with response filter plugins (`papycli.response_filters` entry point)

## Requirements

| Item | Notes |
|------|-------|
| Python | 3.12 or later |

---

## Installation

```bash
pip install papycli
```

### Enable Shell Completion

**bash:**

```bash
# Add to ~/.bashrc or ~/.bash_profile
eval "$(papycli config completion-script bash)"
```

**zsh:**

```bash
# Add to ~/.zshrc
eval "$(papycli config completion-script zsh)"
```

**Git Bash (Windows):**

Git Bash uses MSYS path conversion, which can mangle the output of `$()` command substitution.
Disable it before running the `eval` command:

```bash
# Add to ~/.bashrc or ~/.bash_profile
export MSYS_NO_PATHCONV=1
eval "$(papycli config completion-script bash)"
```

Restart your shell or run `source ~/.bashrc` / `source ~/.zshrc` to apply.

---

## Quick Start — Petstore Demo

This repository includes a demo using the [Swagger Petstore](https://github.com/swagger-api/swagger-petstore).

### 1. Start the Petstore server

```bash
docker compose -f examples/docker-compose.yml up -d
```

The API will be available at `http://localhost:8080/api/v3/`.

### 2. Register the API

```bash
papycli config add examples/petstore-oas3.json
```

### 3. Try some commands

```bash
# List available endpoints
papycli summary

# GET /store/inventory
papycli get /store/inventory

# GET with a path parameter
papycli get /pet/99

# GET with a query parameter
papycli get /pet/findByStatus -q status available

# POST with body parameters
papycli post /pet -p name "My Dog" -p status available -p photoUrls "http://example.com/photo.jpg"

# POST with a raw JSON body
papycli post /pet -d '{"name": "My Dog", "status": "available", "photoUrls": ["http://example.com/photo.jpg"]}'

# Array parameter (repeat the same key)
papycli put /pet -p id 1 -p name "My Dog" -p photoUrls "http://example.com/a.jpg" -p photoUrls "http://example.com/b.jpg" -p status available

# Nested object (dot notation)
papycli put /pet -p id 1 -p name "My Dog" -p category.id 2 -p category.name "Dogs" -p photoUrls "http://example.com/photo.jpg" -p status available

# DELETE /pet/{petId}
papycli delete /pet/1
```

### 4. Tab completion

Once shell completion is enabled, tab completion is available:

```
$ papycli <TAB>
  get  post  put  patch  delete  config  spec  summary

$ papycli get <TAB>
  /pet/findByStatus  /pet/{petId}  /store/inventory  ...

$ papycli get /pet/findByStatus <TAB>
  -q  -p  -H  -d  --summary  --verbose  --check  --check-strict  --response-check

$ papycli get /pet/findByStatus -q <TAB>
  status

$ papycli get /pet/findByStatus -q status <TAB>
  available  pending  sold

$ papycli post /pet -p <TAB>
  name*  photoUrls*  status

$ papycli post /pet -p status <TAB>
  available  pending  sold
```

---

## Adding Your Own API

### Step 1 — Run `config add`

```bash
papycli config add your-api-spec.json
```

This command will:

1. Resolve all `$ref` references in the OpenAPI spec
2. Convert the spec to papycli's internal API definition format
3. Save the result to `$PAPYCLI_CONF_DIR/apis/<name>.json`
4. Create or update `$PAPYCLI_CONF_DIR/papycli.conf`

The API name is derived from the filename (e.g. `your-api-spec.json` → `your-api-spec`).

### Step 2 — Set the base URL

If the spec contains `servers[0].url`, it is used automatically. Otherwise, edit `$PAPYCLI_CONF_DIR/papycli.conf` and set the `url` field:

```json
{
  "default": "your-api-spec",
  "your-api-spec": {
    "openapispec": "your-api-spec.json",
    "apidef": "your-api-spec.json",
    "url": "https://your-api-base-url/"
  }
}
```

### Managing Multiple APIs

```bash
# Register multiple APIs
papycli config add petstore-oas3.json
papycli config add myapi.json

# Switch the active API
papycli config use myapi

# Remove a registered API
papycli config remove petstore-oas3

# Show registered APIs and the current default
papycli config list

# Create a short alias command for the current default API
papycli config alias petcli

# List configured aliases
papycli config alias

# Delete an alias
papycli config alias -d petcli
```

---

## Reference

```
# Configuration management commands
papycli config add <spec-file>             Register an API from an OpenAPI spec file
papycli config remove <api-name>           Remove a registered API
papycli config use <api-name>              Switch the active API
papycli config list                        List registered APIs and current configuration
papycli config log                         Show the current log file path
papycli config log <path>                  Set the log file path
papycli config log --unset                 Disable logging
papycli config alias [alias-name] [spec-name]  Create a command alias for a registered API
papycli config alias                       List configured aliases
papycli config alias -d <alias-name>       Delete an alias
papycli config completion-script <bash|zsh>  Print a shell completion script

# Inspection commands
papycli spec [resource]             Show the raw internal API spec (filter by resource path)
papycli spec --full [resource]      Output the stored OpenAPI spec (filter by resource path if given)
papycli summary [resource]          List available endpoints (filter by resource prefix)
                                      Required params marked with *, array params with []
papycli summary --csv               Output endpoints in CSV format

# API call commands
papycli <method> <resource> [options]

Methods:
  get | post | put | patch | delete

Options:
  -H <header: value>      Custom HTTP header (repeatable)
  -q <name> <value>       Query parameter (repeatable).
                            You can also embed query parameters directly in the
                            resource path: "/pet/findByStatus?status=available"
                            Inline parameters are sent before any -q parameters.
  -p <name> <value>       Body parameter (repeatable)
                            - Values are coerced to the correct JSON type
                              (integer, number, boolean) based on the API spec.
                              Strings are passed as-is.
                            - Repeat the same key to build a JSON array:
                              -p tags foo -p tags bar  →  {"tags":["foo","bar"]}
                            - Use dot notation to build a nested object:
                              -p category.id 1 -p category.name Dogs
                              →  {"category":{"id":"1","name":"Dogs"}}
  -d <json>               Raw JSON body (overrides -p)
  --summary               Show endpoint info without sending a request
  --check                 Validate params before sending (warn on stderr, request is still sent)
  --check-strict          Validate params before sending (warn on stderr, abort with exit 1 on failure)
  --response-check        Validate response status code and body against the OpenAPI spec
                            (warn on stderr; violations do not affect exit code)
  --verbose / -v          Show HTTP status line
  --version               Show version
  --help / -h             Show help

Environment variables:
  PAPYCLI_CONF_DIR        Path to the config directory (default: ~/.papycli)
  PAPYCLI_CUSTOM_HEADER   Custom HTTP headers applied to every request.
                            Separate multiple headers with newlines:
                            export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer token\nX-Tenant: acme'
```

---

## Request Filter Plugins

You can intercept and transform outgoing requests by writing a request filter plugin.

A filter is a callable that receives a `RequestContext` and returns a modified `RequestContext`:

```python
# my_plugin.py
from papycli.filters import RequestContext

def request_filter(ctx: RequestContext) -> RequestContext:
    ctx.headers["X-Request-ID"] = "my-id"
    return ctx
```

Register it in your package's `pyproject.toml`:

```toml
[project.entry-points."papycli.request_filters"]
my-filter = "my_plugin:request_filter"
```

Install the package and filters are applied automatically on every request, sorted by plugin name.

`RequestContext` fields:

| Field | Type | Description |
|-------|------|-------------|
| `method` | `str` | HTTP method (lowercase). Do not modify. |
| `url` | `str` | Full URL with path parameters expanded. |
| `query_params` | `list[tuple[str, str]]` | Query parameters. |
| `body` | `dict \| list \| str \| int \| float \| bool \| None` | JSON request body. |
| `headers` | `dict[str, str]` | Custom HTTP headers. |
| `spec` | `dict \| None` | The matched operation spec entry from the API definition (read-only). `None` if not resolvable. |

---

## Response Filter Plugins

You can inspect and transform incoming responses by writing a response filter plugin.

A filter is a callable that receives a `ResponseContext` and returns a modified `ResponseContext`, or `None` to suppress the response output and stop the filter chain:

```python
# my_plugin.py
from papycli.filters import ResponseContext

def response_filter(ctx: ResponseContext) -> ResponseContext | None:
    if isinstance(ctx.body, dict):
        ctx.body["_status"] = ctx.status_code
    return ctx
```

Returning `None` suppresses the response output entirely and prevents any subsequent filters from running — useful for silencing responses that match certain criteria.

Register it in your package's `pyproject.toml`:

```toml
[project.entry-points."papycli.response_filters"]
my-filter = "my_plugin:response_filter"
```

Install the package and the filters are applied automatically after every response, sorted by plugin name.

`ResponseContext` fields:

| Field | Type | Description |
|-------|------|-------------|
| `method` | `str` | HTTP method used for the request (lowercase). |
| `url` | `str` | Full URL of the request. |
| `status_code` | `int` | HTTP response status code. |
| `reason` | `str` | HTTP response reason phrase (e.g. `"OK"`, `"Not Found"`). |
| `headers` | `dict[str, str]` | Response headers. |
| `body` | `dict \| list \| str \| int \| float \| bool \| None` | Parsed response body. Modify this field to replace the response body. |
| `request_body` | `dict \| list \| str \| int \| float \| bool \| None` | Request body sent to the server (read-only). `None` for requests without a body. |
| `schema` | `dict \| None` | The resolved OpenAPI Response Object for the matched status code (read-only). `None` if no matching definition exists. |

---

## Limitations

- Request bodies are `application/json` only
- Array parameters support scalar element types only (arrays of objects are not supported)
- Dot notation for nested objects supports one level of nesting only
- Pass auth headers via `-H "Authorization: Bearer token"` or the `PAPYCLI_CUSTOM_HEADER` env var

---

## Development

```bash
git clone https://github.com/tmonj1/papycli.git
cd papycli
pip install -e ".[dev]"
```

### Running Tests

These commands assume [uv](https://docs.astral.sh/uv/) is installed. If you set up the environment with `pip` instead, omit the `uv run` prefix and run `pytest` directly.

**Unit tests:**

```bash
uv run pytest
```

**Integration tests:**

The integration tests require the `papycli` binary to be present in `.venv/bin/`. Run `uv sync` first:

```bash
uv sync
uv run pytest -m integration --override-ini addopts= tests/integration/
```

**Run all tests at once:**

```bash
uv sync
uv run pytest --override-ini addopts=
```