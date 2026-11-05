"""AES-256-GCM for OAuth tokens at rest: a leaked database file alone exposes no credentials."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(plain: str, key_b64: str) -> str:
    nonce = os.urandom(12)
    sealed = AESGCM(base64.b64decode(key_b64)).encrypt(nonce, plain.encode(), None)
    return base64.b64encode(nonce + sealed).decode()


def decrypt(token: str, key_b64: str) -> str:
    raw = base64.b64decode(token)
    return AESGCM(base64.b64decode(key_b64)).decrypt(raw[:12], raw[12:], None).decode()
