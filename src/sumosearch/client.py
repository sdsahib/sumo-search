from __future__ import annotations

import sys
import time

import httpx

from sumosearch.exceptions import (
    APIError,
    JobCancelledError,
    JobTimeoutError,
    RateLimitError,
)
from sumosearch.models import (
    DEFAULT_ENDPOINT,
    MAX_POLL_ATTEMPTS,
    POLL_INTERVAL_SECONDS,
    Credentials,
    JobState,
    LogMessage,
    SearchJob,
    SearchJobRequest,
)


class SumoClient:
    def __init__(
        self,
        credentials: Credentials,
        endpoint: str = DEFAULT_ENDPOINT,
        verbose: bool = False,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._verbose = verbose
        self._client = httpx.Client(
            auth=httpx.BasicAuth(credentials.access_id, credentials.access_key),
            timeout=30.0,
        )

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(f"[verbose] {msg}", file=sys.stderr)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SumoClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def create_job(self, request: SearchJobRequest) -> str:
        url = f"{self._endpoint}/search/jobs"
        self._log(f"POST {url}")
        resp = self._client.post(url, json=request.to_api_dict())
        self._log(f"create_job response: HTTP {resp.status_code}")
        self._raise_for_status(resp)
        data = resp.json()
        job_id = str(data["id"])
        self._log(f"job created: id={job_id}")
        return job_id

    def get_job_status(self, job_id: str) -> SearchJob:
        url = f"{self._endpoint}/search/jobs/{job_id}"
        resp = self._client.get(url)
        self._raise_for_status(resp)
        data = resp.json()
        job = SearchJob(
            job_id=job_id,
            state=JobState(data["state"]),
            message_count=data.get("messageCount", 0),
            record_count=data.get("recordCount", 0),
            pending_errors=data.get("pendingErrors", []),
            pending_warnings=data.get("pendingWarnings", []),
        )
        self._log(
            f"poll job={job_id}: state={job.state} messages={job.message_count}"
            + (f" errors={job.pending_errors}" if job.pending_errors else "")
            + (f" warnings={job.pending_warnings}" if job.pending_warnings else "")
        )
        return job

    def get_messages(
        self, job_id: str, offset: int, limit: int
    ) -> list[LogMessage]:
        url = f"{self._endpoint}/search/jobs/{job_id}/messages"
        self._log(f"GET messages job={job_id} offset={offset} limit={limit}")
        resp = self._client.get(url, params={"offset": offset, "limit": limit})
        self._log(f"get_messages response: HTTP {resp.status_code}")
        self._raise_for_status(resp)
        data = resp.json()
        messages = []
        for msg in data.get("messages", []):
            fields = {k: str(v) for k, v in msg.get("map", {}).items()}
            messages.append(LogMessage(fields=fields))
        self._log(f"fetched {len(messages)} messages at offset={offset}")
        return messages

    def delete_job(self, job_id: str) -> None:
        url = f"{self._endpoint}/search/jobs/{job_id}"
        self._log(f"DELETE job={job_id}")
        try:
            resp = self._client.delete(url)
            if resp.status_code == 404:
                self._log(f"delete_job: job={job_id} already gone (404)")
                return
            self._raise_for_status(resp)
            self._log(f"delete_job: job={job_id} deleted (HTTP {resp.status_code})")
        except (APIError, httpx.HTTPError) as exc:
            self._log(f"delete_job: ignored error for job={job_id}: {exc}")

    def fetch_all_messages(
        self,
        job_id: str,
        message_count: int,
        pages: int,
        page_size: int,
        sort: str | None = None,
    ) -> list[LogMessage]:
        all_messages: list[LogMessage] = []
        max_to_fetch = min(pages * page_size, message_count)
        self._log(
            f"fetch_all_messages: job={job_id} available={message_count} "
            f"max_to_fetch={max_to_fetch} (pages={pages}, page_size={page_size})"
        )
        offset = 0
        while offset < max_to_fetch:
            limit = min(page_size, max_to_fetch - offset)
            batch = self.get_messages(job_id, offset, limit)
            all_messages.extend(batch)
            offset += page_size
            if offset >= message_count:
                break

        if sort == "asc":
            all_messages.sort(
                key=lambda m: int(m.fields.get("_messagetime", "0"))
            )
        elif sort == "desc":
            all_messages.sort(
                key=lambda m: int(m.fields.get("_messagetime", "0")),
                reverse=True,
            )

        return all_messages

    def run_search(
        self,
        request: SearchJobRequest,
        pages: int,
        page_size: int,
    ) -> list[LogMessage]:
        job_id = self.create_job(request)
        self._log(f"starting poll loop (max {MAX_POLL_ATTEMPTS} attempts, {POLL_INTERVAL_SECONDS}s interval)")
        force_paused = False
        try:
            for attempt in range(MAX_POLL_ATTEMPTS):
                job = self.get_job_status(job_id)

                if job.state == JobState.DONE:
                    self._log(f"job DONE after {attempt + 1} poll(s); fetching messages")
                    return self.fetch_all_messages(
                        job_id, job.message_count, pages, page_size, request.sort
                    )

                if job.state == JobState.FORCE_PAUSED:
                    force_paused = True
                    self._log("job FORCE_PAUSED (100k limit hit); fetching available messages")
                    messages = self.fetch_all_messages(
                        job_id, job.message_count, pages, page_size, request.sort
                    )
                    print(
                        "Warning: result set truncated at Sumo Logic's "
                        "100,000-message limit.",
                        file=sys.stderr,
                    )
                    return messages

                if job.state == JobState.CANCELLED:
                    self._log(f"job CANCELLED by server after {attempt + 1} poll(s)")
                    raise JobCancelledError(
                        f"search job was cancelled by the server; job ID: {job_id}"
                    )

                self._log(f"sleeping {POLL_INTERVAL_SECONDS}s before next poll (attempt {attempt + 1}/{MAX_POLL_ATTEMPTS})")
                time.sleep(POLL_INTERVAL_SECONDS)
            else:
                self._log(f"poll loop exhausted ({MAX_POLL_ATTEMPTS} attempts)")
                raise JobTimeoutError(
                    f"search job timed out after 300 seconds; job ID: {job_id}"
                )
        finally:
            if not force_paused:
                self.delete_job(job_id)

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code == 401:
            raise APIError(
                "authentication failed (HTTP 401); "
                "check SUMO_ACCESS_ID and SUMO_ACCESS_KEY"
            )
        if resp.status_code == 429:
            raise RateLimitError("rate limit exceeded (HTTP 429); try again later")
        if resp.status_code >= 400:
            raise APIError(f"API error (HTTP {resp.status_code}): {resp.text[:200]}")
