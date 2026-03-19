from __future__ import annotations

from datetime import datetime

from sumosearch.exceptions import ValidationError
from sumosearch.models import API_MAX_PAGE_SIZE, TIMEZONE_ALLOWLIST

_ALLOWED_TZ_DISPLAY = " ".join(sorted(TIMEZONE_ALLOWLIST.keys()))


def validate_timezone(code: str) -> None:
    if code not in TIMEZONE_ALLOWLIST:
        raise ValidationError(
            f"unrecognized timezone code '{code}'; allowed: {_ALLOWED_TZ_DISPLAY}"
        )


def validate_datetime(value: str, flag: str) -> None:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError(f"invalid {flag} datetime: '{value}'")


def validate_time_range(from_time: str, to_time: str) -> None:
    try:
        from_dt = datetime.fromisoformat(from_time)
        to_dt = datetime.fromisoformat(to_time)
    except ValueError:
        return
    if from_dt >= to_dt:
        raise ValidationError("--from must be before --to")


def validate_page_size(value: int) -> None:
    if value < 1 or value > API_MAX_PAGE_SIZE:
        raise ValidationError(f"--page-size must be 1–{API_MAX_PAGE_SIZE}")


def validate_pages(value: int) -> None:
    if value < 1:
        raise ValidationError("--pages must be >= 1")


def validate_sort(value: str | None) -> None:
    if value is not None and value not in ("asc", "desc"):
        raise ValidationError("--sort must be asc or desc")
