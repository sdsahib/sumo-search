# SumoSearch

A CLI tool for fetching and searching logs from [Sumo Logic](https://www.sumologic.com/). Authenticates via environment variables or a local config file, submits asynchronous search jobs, polls for completion, and outputs results as plain text, CSV, or JSON.

Designed as a developer utility that can be invoked directly or by AI assistants (Claude, Copilot) to debug issues from SumoLogic logs.

---

## Requirements

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) package manager
- Sumo Logic Access ID and Access Key

---

## Installation

### Install as a tool (recommended)

```bash
uv tool install sumosearch --from git+https://github.com/sdsahib/sumo-search.git
```

After installation, the `sumosearch` command is available in your shell.

### From source

```bash
git clone https://github.com/sdsahib/sumo-search.git
cd sumo-search
uv sync
```

---

## Configuration

Credentials are resolved in this order:

1. **CLI flags** — `--access-id` / `--access-key`
2. **Environment variables** — `SUMO_ACCESS_ID`, `SUMO_ACCESS_KEY`
3. **Config file** — `~/.sumosearch` (permissions `0600`)

### Interactive setup (recommended)

```bash
sumosearch init
```

This walks you through setting up your credentials and saves them to `~/.sumosearch`. The config file format is a plain key=value file:

```
SUMO_ACCESS_ID=your-access-id
SUMO_ACCESS_KEY=your-access-key
TIMEZONE=UTC
PAGE_SIZE=100
PAGES=1
```

### Environment variables (alternative)

If you prefer not to use a config file, export credentials directly:

```bash
export SUMO_ACCESS_ID="your-access-id"
export SUMO_ACCESS_KEY="your-access-key"
export SUMO_ENDPOINT="https://api.eu.sumologic.com/api/v1"  # optional, non-US deployments only
```

---

## Usage

### Commands

```
sumosearch <COMMAND> [OPTIONS]

Commands:
  init     Interactive credential setup
  fetch    Submit a search job and output results
```

### `sumosearch init`

Interactively configure credentials and defaults. Creates or updates `~/.sumosearch`.

```bash
sumosearch init
```

### `sumosearch fetch`

Submit a Sumo Logic search job, poll for completion, and print results.

```
sumosearch fetch --query QUERY --from FROM --to TO [OPTIONS]

Required:
  --query TEXT        Sumo Logic search query string
  --from DATETIME     Start of time range (ISO 8601)
  --to DATETIME       End of time range (ISO 8601)

Optional:
  --timezone TZ       3-letter timezone code (default: UTC)
  --format FORMAT     Output format: text, json, csv (default: text)
  --sort ORDER        Sort by time: asc (oldest first), desc (newest first)
  --page-size N       Messages per page, 1–10000 (default: 100)
  --pages N           Number of pages to retrieve (default: 1)
  --endpoint URL      API base URL for non-US deployments
  --access-id ID      Override SUMO_ACCESS_ID
  --access-key KEY    Override SUMO_ACCESS_KEY
  -v, --verbose       Print debug info to stderr
```

---

## Examples

**Basic search — last hour of errors:**

```bash
sumosearch fetch \
  --query '_sourceCategory=prod/api level=error' \
  --from 2026-03-20T09:00:00 \
  --to 2026-03-20T10:00:00
```

**JSON output — pipe to `jq`:**

```bash
sumosearch fetch \
  --query '_sourceCategory=prod/api status=500' \
  --from 2026-03-20T00:00:00 \
  --to 2026-03-20T23:59:59 \
  --format json | jq '.[] | .message'
```

**CSV output — save to file:**

```bash
sumosearch fetch \
  --query 'error OR exception' \
  --from 2026-03-19T00:00:00 \
  --to 2026-03-20T00:00:00 \
  --format csv > errors.csv
```

**Sort newest first, fetch 500 results across 5 pages:**

```bash
sumosearch fetch \
  --query '_sourceCategory=payments timeout' \
  --from 2026-03-20T08:00:00 \
  --to 2026-03-20T09:00:00 \
  --sort desc \
  --page-size 100 \
  --pages 5
```

**Non-US deployment with verbose output:**

```bash
sumosearch fetch \
  --query 'pod=checkout-service' \
  --from 2026-03-20T00:00:00 \
  --to 2026-03-20T01:00:00 \
  --endpoint https://api.eu.sumologic.com/api/v1 \
  --timezone CET \
  --verbose
```

---

## Output

- **stdout** — search results (text, JSON, or CSV)
- **stderr** — errors and verbose debug info
- **Exit codes** — `0` on success, non-zero on failure

---

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=sumosearch --cov-report=term-missing

# Lint
uv run ruff check .

# Format check
uv run ruff format --check .

# Type check
uv run mypy --strict src/

# Run CLI locally
uv run sumosearch --help
```

---

## Troubleshooting

**`Error: credentials not found`**
Run `sumosearch init` or set the `SUMO_ACCESS_ID` and `SUMO_ACCESS_KEY` environment variables.

**`Error: endpoint must start with https://`**
Check the `SUMO_ENDPOINT` value or `--endpoint` flag — it must be a full `https://` URL.

**No results returned**
- Verify the time range matches where your logs exist.
- Check that your query syntax is valid in the Sumo Logic UI first.
- Try increasing `--pages` or `--page-size` to retrieve more results.
- Use `--verbose` to inspect the job ID, poll state, and page fetches.

**Config file permissions error**
The config file at `~/.sumosearch` must have `0600` permissions:
```bash
chmod 0600 ~/.sumosearch
```
