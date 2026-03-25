# CLI Reference

## Configuration Management

| Command | Description |
|---------|-------------|
| `papycli config add <spec-file>` | Register an API from an OpenAPI spec file |
| `papycli config remove <api-name>` | Remove a registered API |
| `papycli config use <api-name>` | Switch the active API |
| `papycli config list` | List registered APIs and current configuration |
| `papycli config log` | Show the current log file path |
| `papycli config log <path>` | Set the log file path |
| `papycli config log --unset` | Disable logging |
| `papycli config alias [alias-name] [spec-name]` | Create a command alias for a registered API |
| `papycli config alias` | List configured aliases |
| `papycli config alias -d <alias-name>` | Delete an alias |
| `papycli config completion-script <bash\|zsh>` | Print a shell completion script |

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
| `-p <name> <value>` | Body parameter (repeatable). Values are coerced to the correct JSON type (integer, number, boolean) based on the API spec. Strings are passed as-is. Repeat the same key to build a JSON array. Use dot notation to build a nested object (one level deep). |
| `-d <json>` | Raw JSON body (overrides `-p`) |
| `--summary` | Show endpoint info without sending a request |
| `--check` | Validate params before sending (warn on stderr, request is still sent) |
| `--check-strict` | Validate params before sending (warn on stderr, abort with exit 1 on failure) |
| `--response-check` | Validate response status code and body against the OpenAPI spec (warn on stderr; violations do not affect exit code) |
| `--verbose / -v` | Show HTTP status line |
| `--version` | Show version |
| `--help / -h` | Show help |

### Parameter Examples

```bash
# Repeat the same key to build a JSON array
papycli put /pet -p photoUrls "http://example.com/a.jpg" -p photoUrls "http://example.com/b.jpg"
# → {"photoUrls": ["http://example.com/a.jpg", "http://example.com/b.jpg"]}

# Use dot notation to build a nested object (one level)
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
