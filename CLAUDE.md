# SumoSearch Development Guidelines

## Project Overview

`sumo` — a Sumo Logic search log fetcher CLI. Authenticates via `SUMO_ACCESS_ID` / `SUMO_ACCESS_KEY`, creates asynchronous search jobs, polls for completion, and outputs results as plain text, CSV, or JSON.

Package name: `sumosearch` | Entry point: `sumosearch` CLI | Source: `src/sumosearch/`

## Tech Stack

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| Package manager | `uv` exclusively (no pip, poetry, conda) |
| Build backend | `hatchling` |
| HTTP client | `httpx>=0.27` (no `requests`) |
| Testing | `pytest` + `pytest-cov` + `respx` |
| Linting/formatting | `ruff` (lint + format) |
| Type checking | `mypy --strict` on `src/` |

## Project Structure

```
src/sumosearch/
  __init__.py
  cli.py          # argparse entry point (main)
  client.py       # httpx-based Sumo Logic API client
  auth.py         # credential resolution (env vars, config file)
  config.py       # config file parser (~/.config/sumoutility/config.toml)
  models.py       # dataclasses / typed models
  formatter.py    # output formatting (text, csv, json)
  validation.py   # input validation
  exceptions.py   # custom exception types

tests/
  conftest.py
  unit/
  integration/
```

## Commands

```bash
# Run tests (from project root)
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

## Core Constraints (from constitution)

1. **Credentials** — sourced only from env vars (`SUMO_ACCESS_ID`, `SUMO_ACCESS_KEY`, `SUMO_ENDPOINT`), config file (`~/.config/sumoutility/config.toml`, perms `0600`), or explicit CLI flags. Secrets MUST NOT appear in logs, errors, or tracebacks.

2. **Output** — stdout for data (human-readable by default, JSON via `--output json`), stderr for errors. Exit codes: 0 = success, non-zero = failure.

3. **Dependencies** — minimal; prefer stdlib. New third-party deps require explicit justification in `pyproject.toml`.

4. **Type safety** — all public functions must have type annotations; `mypy --strict` must pass.

5. **Coverage** — must not drop below 80% on new code.

## Code Style

- Python 3.11+, `ruff` enforced, line length 88
- `ruff` rules: `E`, `F`, `I` (isort), `UP` (pyupgrade)
- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, etc.
- No force-pushes to `main`; all merges via PR
