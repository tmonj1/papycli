# papycli — Python CLI for OpenAPI 3.0 REST APIs

`papycli` is an interactive CLI that reads OpenAPI 3.0 specs and lets you call REST API endpoints directly from the terminal.

## Features

- Auto-generates a CLI from any OpenAPI 3.0 spec
- Shell completion for bash and zsh
- Register and switch between multiple APIs

## Requirements

| Item | Notes |
|------|-------|
| Python | 3.12 or later |

No external tools (e.g. `jq`) required. Works with Python and pip alone.

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
  get  post  put  patch  delete  config  summary

$ papycli get <TAB>
  /pet/findByStatus  /pet/{petId}  /store/inventory  ...

$ papycli get /pet/findByStatus <TAB>
  -q  --summary  --help

$ papycli get /pet/findByStatus -q <TAB>
  status

$ papycli get /pet/findByStatus -q status <TAB>
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
papycli config show
```

---

## Reference

```
# Configuration management commands
papycli config add <spec-file>             Register an API from an OpenAPI spec file
papycli config remove <api-name>           Remove a registered API
papycli config use <api-name>              Switch the active API
papycli config show                        Show current configuration
papycli config completion-script <bash|zsh>  Print a shell completion script

# API call commands
papycli summary [resource]          List available endpoints (filter by resource prefix)
                                      Required params marked with *, array params with []
papycli summary --csv               Output endpoints in CSV format
papycli <method> <resource> [options]

Methods:
  get | post | put | patch | delete

Options:
  -H <header: value>      Custom HTTP header (repeatable)
  -q <name> <value>       Query parameter (repeatable)
  -p <name> <value>       Body parameter (repeatable)
                            - Repeat the same key to build a JSON array:
                              -p tags foo -p tags bar  →  {"tags":["foo","bar"]}
                            - Use dot notation to build a nested object:
                              -p category.id 1 -p category.name Dogs
                              →  {"category":{"id":"1","name":"Dogs"}}
  -d <json>               Raw JSON body (overrides -p)
  --summary               Show endpoint info without sending a request
  --version               Show version
  --help / -h             Show help

Environment variables:
  PAPYCLI_CONF_DIR        Path to the config directory (default: ~/.papycli)
  PAPYCLI_CUSTOM_HEADER   Custom HTTP headers applied to every request.
                            Separate multiple headers with newlines:
                            export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer token\nX-Tenant: acme'
```

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

See [CLAUDE.md](CLAUDE.md) for details.
