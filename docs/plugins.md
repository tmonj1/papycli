# Filter Plugins

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

### `RequestContext` Fields

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

### `ResponseContext` Fields

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
