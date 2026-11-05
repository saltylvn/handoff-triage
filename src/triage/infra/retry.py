import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from triage.infra.http import HttpError

_RETRYABLE_STATUS = frozenset({408, 425, 429})


def is_retryable(error: Exception) -> bool:
    if isinstance(error, HttpError):
        return error.status in _RETRYABLE_STATUS or error.status >= 500
    return isinstance(error, httpx.TransportError)


def backoff_s(
    attempt: int, base_s: float, cap_s: float, rand: Callable[[], float] = random.random
) -> float:
    """Full jitter: a random wait up to the exponential ceiling, so clients that failed together
    don't all come back at the same instant."""
    return float(rand() * min(cap_s, base_s * 2 ** (attempt - 1)))


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.5
    cap_s: float = 8.0
    # A longer requested wait goes back to the queue instead of holding the worker.
    max_wait_s: float = 15.0
    sleep: Callable[[float], None] = field(default=time.sleep)
    rand: Callable[[], float] = field(default=random.random)
    retry_on: Callable[[Exception], bool] = field(default=is_retryable)


def with_retry[T](fn: Callable[[], T], policy: RetryPolicy) -> T:
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except Exception as error:
            if attempt >= policy.max_attempts or not policy.retry_on(error):
                raise
            asked = error.retry_after_s if isinstance(error, HttpError) else None
            wait = max(backoff_s(attempt, policy.base_s, policy.cap_s, policy.rand), asked or 0.0)
            if wait > policy.max_wait_s:
                raise
            policy.sleep(wait)
