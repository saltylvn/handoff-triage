"""Slack's signing scheme, reused for our own webhook: HMAC-SHA256 over v0:<timestamp>:<raw body>.
The timestamp is signed too, so a captured request can't be replayed later."""

import hashlib
import hmac

_TOLERANCE_S = 300


def sign(secret: str, timestamp: str, body: bytes) -> str:
    base = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def verify(
    secret: str, timestamp: str | None, signature: str | None, body: bytes, now: float
) -> bool:
    if not timestamp or not signature or not timestamp.isdecimal():
        return False
    if abs(now - int(timestamp)) > _TOLERANCE_S:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), signature)
