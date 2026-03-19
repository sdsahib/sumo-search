# Changelog

## [0.1.0] - 2026-03-18

### Added

- `sumo init` — interactive credential setup, creates `~/.sumo` with `0600` permissions
- `sumo fetch` — submit Sumo Logic search job, poll for completion, paginate results, output as text/JSON/CSV
- Credential resolution: CLI flags > environment variables > config file
- `--format text` (default), `--format json`, `--format csv` output modes
- `--timezone`, `--sort`, `--page-size`, `--pages` parameters
- `--endpoint` / `SUMO_ENDPOINT` for non-US deployments
