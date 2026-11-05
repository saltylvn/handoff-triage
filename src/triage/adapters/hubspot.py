"""HubSpot over OAuth 2.0. Access tokens last 30 minutes; refresh happens automatically, and tokens
are encrypted before they reach the database."""

import time
from collections.abc import Callable
from urllib.parse import urlencode

import httpx

from triage.domain.models import ContactInput, ContactResult, ExistingContact
from triage.infra.crypto import decrypt, encrypt
from triage.infra.http import HttpError, request_json
from triage.infra.retry import RetryPolicy, with_retry
from triage.store import Store

AUTHORIZE_URL = "https://app.hubspot.com/oauth/authorize"
TOKEN_URL = "https://api.hubspot.com/oauth/2026-09/token"  # noqa: S105
API = "https://api.hubapi.com/crm/v3/objects/contacts"
SCOPES = "crm.objects.contacts.read crm.objects.contacts.write"
_PROVIDER = "hubspot"
_REFRESH_MARGIN_S = 60


class NotConnectedError(Exception):
    """No tokens stored yet: run `python -m triage.connect_hubspot`."""


class HubSpotAuth:
    def __init__(
        self,
        client: httpx.Client,
        store: Store,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        encryption_key: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._store = store
        self._id = client_id
        self._secret = client_secret
        self._redirect = redirect_uri
        self._key = encryption_key
        self._clock = clock

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._id,
                "redirect_uri": self._redirect,
                "scope": SCOPES,
                "state": state,
            }
        )
        return f"{AUTHORIZE_URL}?{query}"

    def _grant(self, form: dict[str, str], keep_refresh: str | None = None) -> str:
        data = request_json(
            self._client,
            "hubspot-oauth",
            "POST",
            TOKEN_URL,
            now=self._clock(),
            form={**form, "client_id": self._id, "client_secret": self._secret},
        )
        access = str(data["access_token"])
        refresh = str(data.get("refresh_token") or keep_refresh)
        self._store.save_tokens(
            _PROVIDER,
            encrypt(access, self._key),
            encrypt(refresh, self._key),
            self._clock() + float(data["expires_in"]),
        )
        return access

    def exchange_code(self, code: str) -> None:
        self._grant(
            {"grant_type": "authorization_code", "code": code, "redirect_uri": self._redirect}
        )

    def access_token(self, force_refresh: bool = False) -> str:
        row = self._store.load_tokens(_PROVIDER)
        if row is None:
            raise NotConnectedError
        if not force_refresh and row.expires_at - _REFRESH_MARGIN_S > self._clock():
            return decrypt(row.access_token, self._key)
        refresh = decrypt(row.refresh_token, self._key)
        return self._grant({"grant_type": "refresh_token", "refresh_token": refresh}, refresh)


class HubSpotCrm:
    def __init__(
        self,
        client: httpx.Client,
        auth: HubSpotAuth,
        retry: RetryPolicy | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._auth = auth
        self._retry = retry or RetryPolicy()
        self._clock = clock

    def _call(self, path: str, body: object) -> object:
        def once(force_refresh: bool) -> object:
            token = self._auth.access_token(force_refresh)
            return request_json(
                self._client,
                "hubspot",
                "POST",
                f"{API}{path}",
                now=self._clock(),
                headers={"Authorization": f"Bearer {token}"},
                json_body=body,
            )

        def attempt() -> object:
            try:
                return once(False)
            except HttpError as error:
                if error.status != 401:
                    raise
                return once(True)  # token revoked or expired early: refresh once

        return with_retry(attempt, self._retry)

    def find_contact(self, email: str) -> ExistingContact | None:
        data = self._call(
            "/search",
            {
                "filterGroups": [
                    {"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}
                ],
                "properties": ["lifecyclestage"],
                "limit": 1,
            },
        )
        results = data.get("results") if isinstance(data, dict) else None
        if not results:
            return None
        first = results[0]
        return ExistingContact(
            id=str(first["id"]), lifecycle_stage=first.get("properties", {}).get("lifecyclestage")
        )

    def upsert_contact(self, contact: ContactInput) -> ContactResult:
        """Upsert keyed on email: running this twice updates one contact, never creates two."""
        data = self._call(
            "/batch/upsert",
            {
                "inputs": [
                    {"idProperty": "email", "id": contact.email, "properties": contact.properties}
                ]
            },
        )
        if not isinstance(data, dict) or not data.get("results"):
            raise HttpError("hubspot", 502)
        first = data["results"][0]
        return ContactResult(id=str(first["id"]), created=bool(first.get("new", False)))
