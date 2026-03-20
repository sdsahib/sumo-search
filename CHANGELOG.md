# Changelog

## [0.4.0] - 2026-03-20
- [MINOR] Updated init command to update the host

## [0.3.0] - 2026-03-20
- [MINOR] implemented --version flag to display current version and exit

## [0.2.0] - 2026-03-20
- [MINOR] Added the `--host` config to `init` command
- [MINOR] Added SKILL file for claude

## [0.1.1] - 2026-03-20
- [PATCH] Updated the project name.


## [Unreleased] - 2026-03-20
- [PATCH] Updated Readme with usage examples and troubleshooting tips

## [0.1.0] - 2026-03-19

### Added

- `uv run sumosearch init` — interactive credential setup, creates `~/.sumosearch` with `0600` permissions
- `uv run sumosearch fetch` — submit Sumo Logic search job, poll for completion, paginate results, output as text/JSON/CSV
- Credential resolution: CLI flags > environment variables > config file
- `--format text` (default), `--format json`, `--format csv` output modes
- `--timezone`, `--sort`, `--page-size`, `--pages` parameters
- `--endpoint` / `SUMO_ENDPOINT` for non-US deployments
