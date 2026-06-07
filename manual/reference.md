# CLI Reference

## Global Options

Global options must be placed **before** the subcommand:

```bash
papycli --api petstore get /pet/1   # ✓ correct
papycli get /pet/1 --api petstore   # ✗ Error: No such option: --api
```

| Option | Description |
|--------|-------------|
| `--api <api-name>` | Use the specified API instead of the default |
| `-V / --version` | Show version and exit |
| `-h / --help` | Show help and exit |

## Configuration Management

| Command | Description |
|---------|-------------|
| `papycli config add <spec-file>` | Register an API from an OpenAPI spec file |
| `papycli config add --upgrade <spec-file>` | Update an already-registered API with a new spec; if not yet registered, register it as new |
| `papycli config remove <api-name>` | Remove a registered API |
| `papycli config use <api-name>` | Switch the active API |
| `papycli config list` | List registered APIs and current configuration |
| `papycli config log` | Show the current log file path |
| `papycli config log <path>` | Set the log file path |
| `papycli config log --unset` | Disable logging |
| `papycli config completion-script <bash\|zsh>` | Print a shell completion script |
| `papycli config completion-script --api <api-name> <bash\|zsh>` | Print a completion script for the named CLI (see [Creating a Named CLI](quickstart.md#creating-a-named-cli-for-a-specific-api)) |

## Inspection Commands

| Command | Description |
|---------|-------------|
| `papycli spec [resource]` | Show the raw internal API spec (filter by resource path) |
| `papycli spec --full [resource]` | Output the stored OpenAPI spec (filter by resource path if given) |
| `papycli summary [resource]` | List available endpoints (filter by resource prefix). Required params marked with `*`, array params with `[]` |
| `papycli summary --csv` | Output endpoints in CSV format |

## API Call Commands

```
papycli <method> <resource> [options]
```

**Supported methods:** `get | post | put | patch | delete`

### Options

| Option | Description |
|--------|-------------|
| `-H <header: value>` | Custom HTTP header (repeatable) |
| `-q <name> <value>` | Query parameter (repeatable). You can also embed query parameters directly in the resource path: `/pet/findByStatus?status=available`. Inline parameters are sent before any `-q` parameters. |
| `-p <name> <value>` | Body parameter (repeatable). Values are coerced to the correct JSON type (integer, number, boolean) based on the API spec. Strings are passed as-is. Repeat the same key to build a JSON array. Use dot notation to build a nested object. |
| `-d <json>` | Raw JSON body (overrides `-p`) |
| `--summary` | Show endpoint info without sending a request |
| `--check` | Validate params before sending (warn on stderr, request is still sent) |
| `--check-strict` | Validate params before sending (warn on stderr, abort with exit 1 on failure) |
| `--response-check` | Validate response status code and body against the OpenAPI spec (warn on stderr; violations do not affect exit code) |
| `--verbose / -v` | Show HTTP status line |
| `--help / -h` | Show help for this command |

### Parameter Examples

```bash
# Repeat the same key to build a JSON array
papycli put /pet -p photoUrls "http://example.com/a.jpg" -p photoUrls "http://example.com/b.jpg"
# → {"photoUrls": ["http://example.com/a.jpg", "http://example.com/b.jpg"]}

# Use dot notation to build a nested object
papycli put /pet -p category.id 2 -p category.name "Dogs"
# → {"category": {"id": 2, "name": "Dogs"}}

# Raw JSON body
papycli post /pet -d '{"name": "My Dog", "status": "available"}'
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPYCLI_CONF_DIR` | `~/.papycli` | Path to the config directory |
| `PAPYCLI_CUSTOM_HEADER` | (none) | Custom HTTP headers applied to every request. Separate multiple headers with newlines: `export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer token\nX-Tenant: acme'` |
| `PAPYCLI_DISABLE_DOTENV` | (none) | Set to `1` to disable automatic `.env` file loading |

### `.env` File Auto-loading

On startup, papycli loads environment variables from `.env` files in the following priority order (higher entries win):

1. Shell environment variables (always highest priority)
2. `.env` in the current working directory
3. `.env` in `$PAPYCLI_CONF_DIR`

Set `PAPYCLI_DISABLE_DOTENV=1` to skip `.env` file loading entirely.
