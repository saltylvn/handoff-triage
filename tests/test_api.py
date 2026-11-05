import json
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from triage.api import MAX_BODY_BYTES, create_app
from triage.domain.models import Submission
from triage.fakes import FakeChat
from triage.infra.signature import sign
from triage.store import Store

NOW = 1_000_000.0
SECRET = "w" * 32


class FakeAuth:
    def __init__(self) -> None:
        self.codes: list[str] = []

    def exchange_code(self, code: str) -> None:
        self.codes.append(code)


def app_for(store: Store) -> tuple[TestClient, FakeChat, FakeAuth]:
    chat, auth = FakeChat(), FakeAuth()
    app = create_app(
        store=store,
        chat=chat,
        auth=auth,
        webhook_secret=SECRET,
        slack_signing_secret="slack",
        approvers=frozenset({"U1"}),
        now=lambda: NOW,
    )
    return TestClient(app, raise_server_exceptions=False), chat, auth


def post_signed(client: TestClient, payload: object, secret: str = SECRET) -> int:
    body = json.dumps(payload).encode()
    timestamp = str(int(NOW))
    response = client.post(
        "/webhooks/inbound",
        content=body,
        headers={"x-timestamp": timestamp, "x-signature": sign(secret, timestamp, body)},
    )
    return int(response.status_code)


GOOD = {"email": "a@x.example", "message": "hello"}


def test_webhook_accepts_signed_and_dedupes(store: Store) -> None:
    client, _, _ = app_for(store)
    body = json.dumps(GOOD).encode()
    timestamp = str(int(NOW))
    headers = {"x-timestamp": timestamp, "x-signature": sign(SECRET, timestamp, body)}
    first = client.post("/webhooks/inbound", content=body, headers=headers)
    second = client.post("/webhooks/inbound", content=body, headers=headers)
    assert first.status_code == 202
    assert first.json()["duplicate"] is False
    assert second.json() == {"id": first.json()["id"], "duplicate": True}


def test_webhook_rejects_bad_signature_and_bad_input(store: Store) -> None:
    client, _, _ = app_for(store)
    assert post_signed(client, GOOD, secret="wrong") == 401
    assert post_signed(client, {"email": "nope", "message": "x"}) == 400
    assert client.post("/webhooks/inbound", content=b"{}").status_code == 401


def test_webhook_rejects_oversized_body(store: Store) -> None:
    client, _, _ = app_for(store)
    response = client.post("/webhooks/inbound", content=b"x" * (MAX_BODY_BYTES + 1))
    assert response.status_code == 413


def waiting_item(store: Store) -> str:
    item_id, _ = store.enqueue("k", Submission(email="a@x.example", message="m"), NOW)
    store.claim_next(NOW, 10)
    store.set_status(item_id, "awaiting_approval", NOW, "awaiting_approval")
    return item_id


def click(client: TestClient, item_id: str, user: str = "U1", secret: str = "slack") -> int:
    payload = {
        "user": {"id": user},
        "actions": [{"action_id": "approve", "value": item_id}],
        "container": {"channel_id": "C1", "message_ts": "1.2"},
    }
    body = urlencode({"payload": json.dumps(payload)}).encode()
    timestamp = str(int(NOW))
    response = client.post(
        "/slack/interactions",
        content=body,
        headers={
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sign(secret, timestamp, body),
        },
    )
    return int(response.status_code)


def test_slack_click_approves_once_and_updates_message(store: Store) -> None:
    client, chat, _ = app_for(store)
    item_id = waiting_item(store)
    assert click(client, item_id) == 200
    assert click(client, item_id) == 200
    item = store.get_item(item_id)
    assert item is not None
    assert item.status == "queued"
    assert item.approved_by == "slack:U1"
    assert len(chat.resolved) == 1


def test_slack_click_from_non_approver_is_denied_and_logged(store: Store) -> None:
    client, _, _ = app_for(store)
    item_id = waiting_item(store)
    assert click(client, item_id, user="U999") == 200
    item = store.get_item(item_id)
    assert item is not None
    assert item.status == "awaiting_approval"
    assert "approval_denied" in [e["kind"] for e in store.trace(item_id)]


def test_slack_forged_click_is_rejected(store: Store) -> None:
    client, _, _ = app_for(store)
    item_id = waiting_item(store)
    assert click(client, item_id, secret="forged") == 401
    item = store.get_item(item_id)
    assert item is not None
    assert item.status == "awaiting_approval"


@pytest.mark.parametrize("state", ["", "unknown"])
def test_oauth_callback_requires_valid_state(store: Store, state: str) -> None:
    client, _, auth = app_for(store)
    response = client.get("/oauth/hubspot/callback", params={"state": state, "code": "c"})
    assert response.status_code == 400
    assert auth.codes == []


def test_oauth_callback_exchanges_once(store: Store) -> None:
    client, _, auth = app_for(store)
    store.save_oauth_state("good", NOW + 100)
    params = {"state": "good", "code": "c"}
    assert client.get("/oauth/hubspot/callback", params=params).status_code == 200
    assert client.get("/oauth/hubspot/callback", params=params).status_code == 400
    assert auth.codes == ["c"]


def test_slack_click_with_malformed_user_id_changes_nothing(store: Store) -> None:
    client, chat, _ = app_for(store)
    item_id = waiting_item(store)
    assert click(client, item_id, user="<!channel>") == 200
    item = store.get_item(item_id)
    assert item is not None
    assert item.status == "awaiting_approval"
    assert chat.resolved == []
