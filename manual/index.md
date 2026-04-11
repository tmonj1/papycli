# papycli

**papycli** is an interactive CLI that reads OpenAPI 3.0 specs and lets you call REST API endpoints directly from the terminal.

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

## Limitations

- Request bodies are `application/json` only
- Array parameters support scalar element types only (arrays of objects are not supported)
- Pass auth headers via `-H "Authorization: Bearer token"` or the `PAPYCLI_CUSTOM_HEADER` env var
