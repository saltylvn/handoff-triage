import json
import re
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


class HttpError(Exception):
    def __init__(self, service: str, status: int, retry_after_s: float | None = None) -> None:
        # No response body in the message: it can hold personal data, and this ends up in logs.
        super().__init__(f"{service} responded {status}")
        self.service = service
        self.status = status
        self.retry_after_s = retry_after_s


def parse_retry_after(value: str | None, now: float) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - now)
    except (TypeError, ValueError):
        return None


_GOOGLE_DELAY = re.compile(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"')


def request_json(
    client: httpx.Client,
    service: str,
    method: str,
    url: str,
    *,
    now: float,
    headers: Mapping[str, str] | None = None,
    json_body: Any = None,
    form: Mapping[str, str] | None = None,
    params: Mapping[str, str] | None = None,
    timeout_s: float = 20.0,
) -> Any:
    response = client.request(
        method, url, headers=headers, json=json_body, data=form, params=params, timeout=timeout_s
    )
    if not response.is_success:
        retry_after = parse_retry_after(response.headers.get("retry-after"), now)
        if retry_after is None and (match := _GOOGLE_DELAY.search(response.text)):
            retry_after = float(match.group(1))  # Google puts the wait in the error body
        raise HttpError(service, response.status_code, retry_after)
    if not response.content:
        return None
    try:
        return response.json()
    except json.JSONDecodeError as error:
        raise HttpError(service, 502) from error
