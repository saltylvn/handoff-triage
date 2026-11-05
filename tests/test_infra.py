import base64

import httpx
import pytest

from triage.infra.crypto import decrypt, encrypt
from triage.infra.http import HttpError, parse_retry_after, request_json
from triage.infra.retry import RetryPolicy, backoff_s, is_retryable, with_retry
from triage.infra.signature import sign, verify


def policy(sleeps: list[float], **overrides: float) -> RetryPolicy:
    return RetryPolicy(sleep=sleeps.append, rand=lambda: 1.0, **overrides)  # type: ignore[arg-type]


def test_retries_then_succeeds_with_exponential_waits() -> None:
    sleeps: list[float] = []
    calls = iter([HttpError("x", 500), HttpError("x", 503), None])

    def fn() -> str:
        if error := next(calls):
            raise error
        return "ok"

    assert with_retry(fn, policy(sleeps)) == "ok"
    assert sleeps == [0.5, 1.0]


def test_honors_retry_after_over_backoff() -> None:
    sleeps: list[float] = []
    calls = iter([HttpError("x", 429, 7.0), None])

    def fn() -> str:
        if error := next(calls):
            raise error
        return "ok"

    with_retry(fn, policy(sleeps))
    assert sleeps == [7.0]


def test_long_wait_is_handed_back_to_the_queue() -> None:
    sleeps: list[float] = []

    def fn() -> str:
        raise HttpError("x", 429, 3600.0)

    with pytest.raises(HttpError):
        with_retry(fn, policy(sleeps))
    assert sleeps == []


def test_permanent_errors_are_not_retried() -> None:
    calls = 0

    def fn() -> None:
        nonlocal calls
        calls += 1
        raise HttpError("x", 400)

    with pytest.raises(HttpError):
        with_retry(fn, policy([]))
    assert calls == 1


def test_gives_up_after_max_attempts() -> None:
    calls = 0

    def fn() -> None:
        nonlocal calls
        calls += 1
        raise HttpError("x", 500)

    with pytest.raises(HttpError):
        with_retry(fn, policy([]))
    assert calls == 4


def test_classification_of_errors() -> None:
    assert is_retryable(httpx.ConnectError("down"))
    assert is_retryable(HttpError("x", 429))
    assert not is_retryable(HttpError("x", 404))
    assert not is_retryable(ValueError("bug"))


def test_backoff_is_capped() -> None:
    assert backoff_s(20, 0.5, 8.0, lambda: 1.0) == 8.0


def test_parse_retry_after() -> None:
    assert parse_retry_after("12", 0) == 12
    assert parse_retry_after("Thu, 01 Jan 1970 00:01:40 GMT", 40.0) == 60.0
    assert parse_retry_after("soon", 0) is None
    assert parse_retry_after(None, 0) is None


def test_error_carries_google_retry_delay_but_not_the_body() -> None:
    body = '{"error":{"message":"secret user text","details":[{"retryDelay":"34s"}]}}'
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429, text=body)))
    with pytest.raises(HttpError) as caught:
        request_json(client, "gemini", "POST", "https://x.example", now=0.0)
    assert caught.value.retry_after_s == 34
    assert "secret" not in str(caught.value)


def test_signature_accepts_valid_and_rejects_tampering_and_replay() -> None:
    signature = sign("key", "1000", b"body")
    assert verify("key", "1000", signature, b"body", 1000)
    assert not verify("key", "1000", signature, b"changed", 1000)
    assert not verify("other", "1000", signature, b"body", 1000)
    assert not verify("key", "1000", signature, b"body", 1000 + 301)
    assert not verify("key", None, signature, b"body", 1000)
    assert not verify("key", "abc", signature, b"body", 1000)


def test_crypto_round_trip_and_tamper_detection() -> None:
    key = base64.b64encode(b"k" * 32).decode()
    sealed = encrypt("token", key)
    assert "token" not in sealed
    assert decrypt(sealed, key) == "token"
    raw = bytearray(base64.b64decode(sealed))
    raw[-1] ^= 1
    with pytest.raises(Exception):  # noqa: B017
        decrypt(base64.b64encode(bytes(raw)).decode(), key)
