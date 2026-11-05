"""Slack Web API: summaries, approval buttons, and finding an earlier post by its metadata tag."""

import time
from collections.abc import Callable
from typing import Any

import httpx

from triage.domain.models import ChatMessage, PostResult
from triage.infra.http import request_json
from triage.infra.retry import RetryPolicy, with_retry

_API = "https://slack.com/api"
_EVENT_TYPE = "triage_item"


class SlackApiError(Exception):
    """Slack answered 200 with ok: false, such as channel_not_found. Retrying won't help."""


def escape(text: str) -> str:
    """Slack's required escaping. Without it, a message containing <!channel> pings everyone."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_blocks(message: ChatMessage) -> list[dict[str, Any]]:
    heading = "Needs approval" if message.kind == "approval_request" else "Handled automatically"
    facts = (
        f"*{heading}* · {message.category} · {message.urgency} urgency · "
        f"{message.confidence:.0%} confidence\n*From:* {escape(message.sender)}\n"
        f"{escape(message.summary)}"
    )
    if message.reasons:
        facts += f"\n*Why a person is needed:* {escape(', '.join(message.reasons))}"
    if message.crm_contact_id:
        facts += f"\n*HubSpot contact:* {escape(message.crm_contact_id)}"
    blocks: list[dict[str, Any]] = [{"type": "section", "text": {"type": "mrkdwn", "text": facts}}]
    if message.kind == "approval_request":
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "approve",
                        "value": message.item_id,
                        "style": "primary",
                        "text": {"type": "plain_text", "text": "Approve"},
                    },
                    {
                        "type": "button",
                        "action_id": "reject",
                        "value": message.item_id,
                        "text": {"type": "plain_text", "text": "Reject"},
                    },
                ],
            }
        )
    return blocks


class SlackChat:
    def __init__(
        self,
        client: httpx.Client,
        token: str,
        channel: str,
        retry: RetryPolicy | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._token = token
        self._channel = channel
        self._retry = retry or RetryPolicy()
        self._clock = clock

    def _call(self, method: str, http: str, **kwargs: Any) -> dict[str, Any]:
        data: dict[str, Any] = with_retry(
            lambda: request_json(
                self._client,
                "slack",
                http,
                f"{_API}/{method}",
                now=self._clock(),
                headers={"Authorization": f"Bearer {self._token}"},
                **kwargs,
            ),
            self._retry,
        )
        if not data.get("ok"):
            raise SlackApiError(str(data.get("error", "unknown_error")))
        return data

    def post(self, message: ChatMessage) -> PostResult:
        data = self._call(
            "chat.postMessage",
            "POST",
            json_body={
                "channel": self._channel,
                "text": f"{message.category}: {escape(message.summary)}",
                "blocks": render_blocks(message),
                "unfurl_links": False,
                "metadata": {
                    "event_type": _EVENT_TYPE,
                    "event_payload": {"item_id": message.item_id, "kind": message.kind},
                },
            },
        )
        return PostResult(ts=str(data["ts"]))

    def find_posted(self, item_id: str, kind: str, since: float) -> PostResult | None:
        data = self._call(
            "conversations.history",
            "GET",
            params={
                "channel": self._channel,
                "oldest": str(since - 5),
                "include_all_metadata": "true",
                "limit": "200",
            },
        )
        for message in data.get("messages", []):
            meta = message.get("metadata") or {}
            payload = meta.get("event_payload") or {}
            if (
                meta.get("event_type") == _EVENT_TYPE
                and payload.get("item_id") == item_id
                and payload.get("kind") == kind
            ):
                return PostResult(ts=str(message["ts"]), recovered=True)
        return None

    def mark_resolved(self, channel: str, ts: str, text: str) -> None:
        self._call(
            "chat.update",
            "POST",
            json_body={"channel": channel, "ts": ts, "text": escape(text), "blocks": []},
        )
