# Development

## Setup

```bash
git clone https://github.com/tmonj1/papycli.git
cd papycli
pip install -e ".[dev]"
```

## Running Tests

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

## Tools

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `ruff` | Lint + format |
| `mypy` | Type checking |

## Building the Documentation

To build the documentation locally, install `mkdocs-material` and run:

```bash
pip install mkdocs-material
mkdocs serve
```

This starts a local server at `http://127.0.0.1:8000/` with live reload.
