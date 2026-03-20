from __future__ import annotations

import argparse
import getpass
import os
import sys

from sumosearch import __version__
from sumosearch.auth import resolve_credentials
from sumosearch.client import SumoClient
from sumosearch.config import DEFAULT_CONFIG_PATH, load_config, save_config
from sumosearch.exceptions import ConfigError, SumoSearchError
from sumosearch.formatter import format_messages
from sumosearch.models import (
    DEFAULT_ENDPOINT,
    DEFAULT_PAGE_SIZE,
    DEFAULT_PAGES,
    TIMEZONE_ALLOWLIST,
    Config,
    SearchJobRequest,
)
from sumosearch.validation import (
    validate_datetime,
    validate_page_size,
    validate_pages,
    validate_sort,
    validate_time_range,
    validate_timezone,
)

_ALLOWED_TZ = " ".join(sorted(TIMEZONE_ALLOWLIST.keys()))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sumosearch",
        description="Sumo Logic search log fetcher CLI",
    )
    parser.add_argument(
        "--version", action="version", version=f"sumosearch {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # -- init subcommand --
    init = subparsers.add_parser(
        "init",
        help="Interactive credential setup — creates or updates ~/.sumosearch",
    )
    init.add_argument(
        "--host",
        default=None,
        metavar="URL",
        help=f"API base URL for non-US deployments (default: {DEFAULT_ENDPOINT})",
    )

    # -- fetch subcommand --
    fetch = subparsers.add_parser(
        "fetch",
        help="Submit a search job, poll for completion, and output results",
    )
    fetch.add_argument("--query", required=True, help="Sumo Logic search query string")
    fetch.add_argument(
        "--from",
        dest="from_time",
        required=True,
        metavar="FROM",
        help="Start of time range (ISO 8601, e.g. 2026-01-01T00:00:00)",
    )
    fetch.add_argument(
        "--to",
        dest="to_time",
        required=True,
        metavar="TO",
        help="End of time range (ISO 8601, e.g. 2026-01-01T23:59:59)",
    )
    fetch.add_argument(
        "--timezone",
        default=None,
        metavar="TZ",
        help=f"3-letter timezone code. Allowed: {_ALLOWED_TZ}. "
        f"Resolves: flag > SUMO_TIMEZONE env > config > UTC",
    )
    fetch.add_argument(
        "--sort",
        choices=["asc", "desc"],
        default=None,
        help="Result ordering by _messagetime (applied client-side). "
        "asc = oldest first, desc = newest first. Default: API order.",
    )
    fetch.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    fetch.add_argument(
        "--page-size",
        dest="page_size",
        type=int,
        default=None,
        metavar="N",
        help="Messages per page (1–10000). "
        "Resolves: flag > SUMO_PAGE_SIZE env > config > 100",
    )
    fetch.add_argument(
        "--pages",
        type=int,
        default=None,
        metavar="N",
        help="Pages to retrieve. "
        "Resolves: flag > SUMO_PAGES env > config > 1",
    )
    fetch.add_argument(
        "--access-id",
        dest="access_id",
        default=None,
        metavar="ID",
        help="Override SUMO_ACCESS_ID (credentials never shown in defaults)",
    )
    fetch.add_argument(
        "--access-key",
        dest="access_key",
        default=None,
        metavar="KEY",
        help="Override SUMO_ACCESS_KEY (credentials never shown in defaults)",
    )
    fetch.add_argument(
        "--endpoint",
        default=None,
        metavar="URL",
        help=f"API base URL for non-US deployments. "
        f"Resolves: flag > SUMO_ENDPOINT env > {DEFAULT_ENDPOINT}",
    )
    fetch.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Print debug info to stderr (credential source, job ID, poll state, page fetches)",
    )

    return parser


def _handle_init(args: argparse.Namespace) -> int:
    config_path = DEFAULT_CONFIG_PATH
    existing: Config | None = None
    if config_path.exists():
        try:
            existing = load_config(config_path)
        except ConfigError:
            existing = None

    print("Configuring sumosearch credentials.", file=sys.stderr)
    print(
        "Press Enter to keep the existing value (shown in brackets).",
        file=sys.stderr,
    )

    def prompt_visible(label: str, default: str | None) -> str:
        hint = f" [{default}]" if default else ""
        value = input(f"{label}{hint}: ").strip()
        return value if value else (default or "")

    def prompt_masked(label: str, has_existing: bool) -> str | None:
        hint = " [hidden — press Enter to keep]" if has_existing else ""
        try:
            value = getpass.getpass(f"{label}{hint}: ")
        except getpass.GetPassWarning:
            print(
                "Error: cannot securely mask SUMO_ACCESS_KEY in this terminal. "
                "Set the SUMO_ACCESS_KEY environment variable instead.",
                file=sys.stderr,
            )
            return None
        return value.strip() if value.strip() else None

    access_id = prompt_visible(
        "SUMO_ACCESS_ID",
        existing.sumo_access_id if existing else None,
    )
    if not access_id:
        print("Error: SUMO_ACCESS_ID is required", file=sys.stderr)
        return 1

    raw_key = prompt_masked("SUMO_ACCESS_KEY", has_existing=existing is not None)
    if raw_key is None and existing is None:
        return 1
    access_key = raw_key if raw_key else (existing.sumo_access_key if existing else "")
    if not access_key:
        print("Error: SUMO_ACCESS_KEY is required", file=sys.stderr)
        return 1

    tz_default = existing.timezone if existing else "UTC"
    timezone = prompt_visible("TIMEZONE", tz_default) or tz_default
    try:
        validate_timezone(timezone)
    except SumoSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    ps_default = str(existing.page_size) if existing else "100"
    ps_str = prompt_visible("PAGE_SIZE", ps_default) or ps_default
    try:
        page_size = int(ps_str)
        validate_page_size(page_size)
    except (ValueError, SumoSearchError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    pages_default = str(existing.pages) if existing else "1"
    pages_str = prompt_visible("PAGES", pages_default) or pages_default
    try:
        pages = int(pages_str)
        validate_pages(pages)
    except (ValueError, SumoSearchError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    host_default = (
        args.host
        if args.host is not None
        else (existing.endpoint if existing else DEFAULT_ENDPOINT)
    )
    endpoint = prompt_visible("ENDPOINT", host_default) or host_default
    if not endpoint.startswith("https://"):
        print(
            f"Error: endpoint must start with https://: {endpoint}",
            file=sys.stderr,
        )
        return 1

    cfg = Config(
        sumo_access_id=access_id,
        sumo_access_key=access_key,
        timezone=timezone,
        page_size=page_size,
        pages=pages,
        endpoint=endpoint,
    )
    try:
        save_config(cfg, config_path)
    except SumoSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Configuration saved to {config_path}", file=sys.stderr)
    return 0


def _resolve_fetch_defaults(
    args: argparse.Namespace,
) -> tuple[int, int, str, str, Config | None]:
    cfg: Config | None = None
    try:
        cfg = load_config()
    except (ConfigError, SumoSearchError):
        pass

    # page_size: CLI > env > config > default
    if args.page_size is not None:
        page_size = args.page_size
        _page_size_src = "CLI flag"
    elif "SUMO_PAGE_SIZE" in os.environ:
        try:
            page_size = int(os.environ["SUMO_PAGE_SIZE"])
        except ValueError:
            page_size = DEFAULT_PAGE_SIZE
        _page_size_src = "SUMO_PAGE_SIZE env"
    elif cfg is not None:
        page_size = cfg.page_size
        _page_size_src = "config file"
    else:
        page_size = DEFAULT_PAGE_SIZE
        _page_size_src = "default"

    # pages: CLI > env > config > default
    if args.pages is not None:
        pages = args.pages
        _pages_src = "CLI flag"
    elif "SUMO_PAGES" in os.environ:
        try:
            pages = int(os.environ["SUMO_PAGES"])
        except ValueError:
            pages = DEFAULT_PAGES
        _pages_src = "SUMO_PAGES env"
    elif cfg is not None:
        pages = cfg.pages
        _pages_src = "config file"
    else:
        pages = DEFAULT_PAGES
        _pages_src = "default"

    # timezone: CLI > env > config > default
    if args.timezone is not None:
        timezone = args.timezone
        _tz_src = "CLI flag"
    elif "SUMO_TIMEZONE" in os.environ:
        timezone = os.environ["SUMO_TIMEZONE"]
        _tz_src = "SUMO_TIMEZONE env"
    elif cfg is not None:
        timezone = cfg.timezone
        _tz_src = "config file"
    else:
        timezone = "UTC"
        _tz_src = "default"

    # endpoint: CLI > env > config > default
    if args.endpoint is not None:
        endpoint = args.endpoint
        _ep_src = "CLI flag"
    elif "SUMO_ENDPOINT" in os.environ:
        endpoint = os.environ["SUMO_ENDPOINT"]
        _ep_src = "SUMO_ENDPOINT env"
    elif cfg is not None:
        endpoint = cfg.endpoint
        _ep_src = "config file"
    else:
        endpoint = DEFAULT_ENDPOINT
        _ep_src = "default"

    if getattr(args, "verbose", False):
        print(f"[verbose] config file: {'loaded' if cfg is not None else 'not found'}", file=sys.stderr)
        print(f"[verbose] page_size={page_size} (source: {_page_size_src})", file=sys.stderr)
        print(f"[verbose] pages={pages} (source: {_pages_src})", file=sys.stderr)
        print(f"[verbose] timezone={timezone} (source: {_tz_src})", file=sys.stderr)
        print(f"[verbose] endpoint={endpoint} (source: {_ep_src})", file=sys.stderr)

    return page_size, pages, timezone, endpoint, cfg


def _handle_fetch(args: argparse.Namespace) -> int:
    verbose: bool = getattr(args, "verbose", False)
    page_size, pages, timezone, endpoint, _cfg = _resolve_fetch_defaults(args)

    # Validate endpoint
    if not endpoint.startswith("https://"):
        print(
            f"Error: endpoint must start with https://: {endpoint}",
            file=sys.stderr,
        )
        return 1

    # Validate all inputs before any API call
    try:
        validate_datetime(args.from_time, "--from")
        validate_datetime(args.to_time, "--to")
        validate_time_range(args.from_time, args.to_time)
        validate_timezone(timezone)
        validate_page_size(page_size)
        validate_pages(pages)
        validate_sort(args.sort)
    except SumoSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if verbose:
        print(f"[verbose] query: {args.query!r}", file=sys.stderr)
        print(f"[verbose] time range: {args.from_time} → {args.to_time}", file=sys.stderr)
        print(f"[verbose] sort: {args.sort or 'API order'}", file=sys.stderr)
        print(f"[verbose] format: {args.fmt}", file=sys.stderr)

    try:
        creds = resolve_credentials(
            access_id_flag=args.access_id,
            access_key_flag=args.access_key,
        )
    except SumoSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if verbose:
        if args.access_id:
            cred_src = "CLI flag"
        elif os.environ.get("SUMO_ACCESS_ID"):
            cred_src = "environment variable"
        else:
            cred_src = "config file"
        print(f"[verbose] credentials resolved from: {cred_src}", file=sys.stderr)

    request = SearchJobRequest(
        query=args.query,
        from_time=args.from_time,
        to_time=args.to_time,
        time_zone=timezone,
        sort=args.sort,
    )

    try:
        with SumoClient(credentials=creds, endpoint=endpoint, verbose=verbose) as client:
            messages = client.run_search(request, pages=pages, page_size=page_size)
    except SumoSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error: network error: {exc}", file=sys.stderr)
        return 1

    if verbose:
        print(f"[verbose] total messages returned: {len(messages)}", file=sys.stderr)

    output = format_messages(messages, args.fmt)
    print(output)
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        if args.command == "init":
            sys.exit(_handle_init(args))
        elif args.command == "fetch":
            sys.exit(_handle_fetch(args))
        else:
            parser.print_help(sys.stderr)
            sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
