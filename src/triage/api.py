"""The public surface. Routes verify, validate, record and answer fast; the worker does the slow
work. Senders see only coarse errors; details stay in the server log."""

import json
import logging
from collections.abc import Callable
from typing import Literal, Protocol
from urllib.parse import parse_qs

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from triage.domain.idempotency import idempotency_key
from triage.domain.models import Submission
from triage.domain.ports import Chat
from triage.infra.signature import verify
from triage.store import Store

logger = logging.getLogger("triage.api")
MAX_BODY_BYTES = 64 * 1024


class OAuthExchange(Protocol):
    def exchange_code(self, code: str) -> None: ...


class _SlackAction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action_id: Literal["approve", "reject"]
    value: str


class _SlackUser(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(pattern=r"^[A-Z0-9]+$")  # goes into a mention, so only Slack's ID characters


class _SlackContainer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel_id: str
    message_ts: str


class _SlackInteraction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user: _SlackUser
    actions: list[_SlackAction]
    container: _SlackContainer


def create_app(
    *,
    store: Store,
    chat: Chat,
    auth: OAuthExchange,
    webhook_secret: str,
    slack_signing_secret: str,
    approvers: frozenset[str],
    now: Callable[[], float],
) -> FastAPI:
    app = FastAPI(title="Multi Agent Triage", docs_url=None, redoc_url=None, openapi_url=None)

    async def read_signed(request: Request, secret: str, ts_header: str, sig_header: str) -> bytes:
        declared = request.headers.get("content-length")
        if declared and declared.isdecimal() and int(declared) > MAX_BODY_BYTES:
            raise _Reject(413)
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            raise _Reject(413)
        timestamp = request.headers.get(ts_header)
        signature = request.headers.get(sig_header)
        if not verify(secret, timestamp, signature, body, now()):
            raise _Reject(401)
        return body

    @app.exception_handler(Exception)
    async def unexpected(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=error)
        return JSONResponse({"error": "internal_error"}, status_code=500)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks/inbound")
    async def inbound(request: Request) -> Response:
        try:
            body = await read_signed(request, webhook_secret, "x-timestamp", "x-signature")
        except _Reject as reject:
            return JSONResponse({"error": "rejected"}, status_code=reject.status)
        try:
            submission = Submission.model_validate_json(body)
        except ValidationError:
            return JSONResponse({"error": "invalid_submission"}, status_code=400)
        item_id, created = await run_in_threadpool(
            store.enqueue, idempotency_key(submission), submission, now()
        )
        return JSONResponse({"id": item_id, "duplicate": not created}, status_code=202)

    @app.post("/slack/interactions")
    async def interactions(request: Request, background: BackgroundTasks) -> Response:
        try:
            body = await read_signed(
                request, slack_signing_secret, "x-slack-request-timestamp", "x-slack-signature"
            )
        except _Reject as reject:
            return JSONResponse({"error": "rejected"}, status_code=reject.status)
        try:
            payload = parse_qs(body.decode()).get("payload", [""])[0]
            event = _SlackInteraction.model_validate(json.loads(payload))
            action = event.actions[0]
        except (ValidationError, json.JSONDecodeError, IndexError):
            return Response(status_code=200)  # not an action we handle

        if event.user.id not in approvers:
            await run_in_threadpool(
                store.log, action.value, now(), "approval_denied", f"slack:{event.user.id}", {}
            )
            return Response(status_code=200)

        approved = action.action_id == "approve"
        applied = await run_in_threadpool(
            store.resolve_approval, action.value, approved, f"slack:{event.user.id}", now()
        )
        if applied:
            verb = "Approved" if approved else "Rejected"
            background.add_task(
                _safe_mark,
                chat,
                event.container.channel_id,
                event.container.message_ts,
                f"{verb} by <@{event.user.id}>",
            )
        return Response(status_code=200)  # Slack expects this within 3 seconds

    @app.get("/oauth/hubspot/callback")
    def hubspot_callback(state: str = "", code: str = "") -> HTMLResponse:
        # state proves this callback answers a flow we started (CSRF protection).
        if not state or not code or not store.consume_oauth_state(state, now()):
            return HTMLResponse("Invalid or expired connection link.", status_code=400)
        auth.exchange_code(code)
        return HTMLResponse("HubSpot connected. You can close this tab.")

    return app


class _Reject(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


def _safe_mark(chat: Chat, channel: str, ts: str, text: str) -> None:
    try:
        chat.mark_resolved(channel, ts, text)
    except Exception:
        logger.exception("Could not update the Slack message")  # cosmetic: the decision is saved
