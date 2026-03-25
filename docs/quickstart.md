# Quick Start

## Petstore Demo

This repository includes a demo using the [Swagger Petstore](https://github.com/swagger-api/swagger-petstore).

### 1. Start the Petstore server

```bash
docker compose -f examples/petstore/docker-compose.yml up -d
```

The API will be available at `http://localhost:8080/api/v3/`.

### 2. Register the API

```bash
papycli config add examples/petstore/petstore-oas3.json
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

## Managing Multiple APIs

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
