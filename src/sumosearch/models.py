from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

TIMEZONE_ALLOWLIST: dict[str, str] = {
    "UTC": "UTC",
    "GMT": "GMT",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
}

POLL_INTERVAL_SECONDS: int = 5
MAX_POLL_ATTEMPTS: int = 60
DEFAULT_PAGE_SIZE: int = 100
DEFAULT_PAGES: int = 1
API_MAX_PAGE_SIZE: int = 10_000
DEFAULT_ENDPOINT: str = "https://api.sumologic.com/api/v1"


@dataclass
class Config:
    sumo_access_id: str
    sumo_access_key: str
    timezone: str = "UTC"
    page_size: int = 100
    pages: int = 1


@dataclass
class Credentials:
    access_id: str
    access_key: str

    def __repr__(self) -> str:
        return "Credentials(access_id=<masked>, access_key=<masked>)"


@dataclass
class SearchJobRequest:
    query: str
    from_time: str
    to_time: str
    time_zone: str = "UTC"
    by_receipt_time: bool = False
    sort: str | None = None

    def to_api_dict(self) -> dict[str, str | bool]:
        iana = TIMEZONE_ALLOWLIST.get(self.time_zone, self.time_zone)
        return {
            "query": self.query,
            "from": self.from_time,
            "to": self.to_time,
            "timeZone": iana,
        }


class JobState(StrEnum):
    NOT_STARTED = "NOT STARTED"
    GATHERING_RESULTS = "GATHERING RESULTS"
    FORCE_PAUSED = "FORCE PAUSED"
    DONE = "DONE GATHERING RESULTS"
    CANCELLED = "CANCELLED"


@dataclass
class SearchJob:
    job_id: str
    state: JobState
    message_count: int = 0
    record_count: int = 0
    pending_errors: list[str] = field(default_factory=list)
    pending_warnings: list[str] = field(default_factory=list)


@dataclass
class LogMessage:
    fields: dict[str, str]

    @property
    def raw(self) -> str:
        return self.fields.get("_raw", "")

    @property
    def timestamp(self) -> str:
        return self.fields.get("_messagetime", "")


@dataclass
class QueryParams:
    query: str
    from_time: str
    to_time: str
    timezone: str = "UTC"
    sort: str | None = None
    format: str = "text"
    page_size: int = DEFAULT_PAGE_SIZE
    pages: int = DEFAULT_PAGES
    access_id: str | None = None
    access_key: str | None = None
    endpoint: str | None = None
