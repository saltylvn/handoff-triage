"""The outside enrichment API: RDAP, the public successor to WHOIS. Free, no key, and a brand-new
domain on a large sales inquiry is a useful warning sign."""

import time
from collections.abc import Callable
from datetime import datetime

import httpx

from triage.domain.email import is_lookup_safe_domain
from triage.infra.http import HttpError, request_json
from triage.infra.retry import RetryPolicy, with_retry


class RdapDomainInfo:
    def __init__(
        self,
        client: httpx.Client,
        retry: RetryPolicy | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._retry = retry or RetryPolicy(max_attempts=2, max_wait_s=2.0)
        self._clock = clock

    def age_days(self, domain: str) -> int | None:
        if not is_lookup_safe_domain(domain):
            return None
        try:
            data = with_retry(
                lambda: request_json(
                    self._client,
                    "rdap",
                    "GET",
                    f"https://rdap.org/domain/{domain}",
                    now=self._clock(),
                    timeout_s=8.0,
                ),
                self._retry,
            )
        except HttpError as error:
            if error.status == 404:
                return None
            raise
        for event in data.get("events", []):
            if event.get("eventAction") == "registration":
                registered = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                return max(0, int((self._clock() - registered.timestamp()) // 86_400))
        return None
