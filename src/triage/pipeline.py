"""The workflow as resumable steps. Each step's result is saved; a retry skips finished steps, so a
crash at any point resumes where it stopped instead of repeating side effects."""

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from triage.domain.email import email_domain, is_free_mail, is_lookup_safe_domain
from triage.domain.models import (
    ChatMessage,
    Classification,
    ContactInput,
    ContactResult,
    Enrichment,
    Item,
    PostResult,
    Route,
    Submission,
    Triage,
)
from triage.domain.ports import Chat, Classifier, Crm, DomainInfo, ModelOutputError
from triage.domain.routing import Policy, decide_route
from triage.infra.http import HttpError
from triage.infra.retry import backoff_s, is_retryable
from triage.store import Store

logger = logging.getLogger("triage.pipeline")
MAX_ITEM_ATTEMPTS = 6
LEASE_S = 180.0


@dataclass(frozen=True)
class Deps:
    store: Store
    classifier: Classifier
    domains: DomainInfo
    crm: Crm
    chat: Chat
    policy: Policy
    now: Callable[[], float]


@dataclass(frozen=True)
class StepContext:
    resumed: bool  # a previous attempt started this step and never recorded finishing it
    started_at: float


def _run_step[T: BaseModel](
    deps: Deps,
    item_id: str,
    name: str,
    model: type[T],
    fn: Callable[[StepContext], T],
    describe: Callable[[T], tuple[str, dict[str, Any]]] | None = None,
) -> T:
    prior = deps.store.get_step(item_id, name)
    if prior and prior.status == "done" and prior.result is not None:
        return model.model_validate_json(prior.result)
    started_at = prior.started_at if prior else deps.now()
    if not prior:
        deps.store.start_step(item_id, name, started_at)
    result = fn(StepContext(resumed=prior is not None, started_at=started_at))
    decision = describe(result) if describe else None
    deps.store.complete_step(item_id, name, result.model_dump_json(), deps.now(), decision)
    return result


def _classify(deps: Deps, submission: Submission) -> Classification:
    try:
        return deps.classifier.classify(submission)
    except ModelOutputError:
        # Never guess. An unusable answer has zero confidence, so it goes to a person.
        fallback = Triage(
            category="other",
            urgency="normal",
            sensitive=False,
            confidence=0.0,
            company=None,
            team_size=None,
            budget_usd=None,
            summary="The model's answer was unusable. Please read the original message.",
        )
        return Classification(triage=fallback, usage=None, invalid_output=True)


def _enrich(deps: Deps, submission: Submission) -> Enrichment:
    domain = email_domain(submission.email)
    free = is_free_mail(domain)
    degraded: list[str] = []
    age: int | None = None
    if not free and is_lookup_safe_domain(domain):
        try:
            age = deps.domains.age_days(domain)
        except HttpError:
            degraded.append("domain_age")  # nice to have: never block a lead on this
    # Not caught on purpose: whether this is an existing customer changes the route, so a failed
    # lookup retries the item rather than guessing.
    existing = deps.crm.find_contact(submission.email.lower())
    return Enrichment(
        email_domain=domain,
        is_free_mail=free,
        domain_age_days=age,
        existing_contact=existing,
        degraded=degraded,
    )


def _post_once(deps: Deps, message: ChatMessage, step: str) -> PostResult:
    """Slack has no idempotency key. If an earlier attempt started this step, look for its message
    (tagged with the item ID) before posting again."""

    def attempt(ctx: StepContext) -> PostResult:
        if ctx.resumed:
            found = deps.chat.find_posted(message.item_id, message.kind, ctx.started_at)
            if found:
                return found
        return deps.chat.post(message)

    return _run_step(
        deps,
        message.item_id,
        step,
        PostResult,
        attempt,
        lambda r: ("chat_posted", {"kind": message.kind, "recovered": r.recovered}),
    )


def _contact_input(submission: Submission, triage: Triage, enrichment: Enrichment) -> ContactInput:
    first, _, last = (submission.name or "").partition(" ")
    company = triage.company or submission.company
    props = {"firstname": first, "lastname": last, "company": company, "message": triage.summary}
    # Only a brand-new sales contact gets a lifecycle stage: never downgrade an existing customer.
    if triage.category == "sales_lead" and enrichment.existing_contact is None:
        props["lifecyclestage"] = "lead"
    return ContactInput(
        email=submission.email.lower(), properties={k: v for k, v in props.items() if v}
    )


def process_item(item: Item, deps: Deps) -> None:
    item_id, submission = item.id, item.payload

    classified = _run_step(
        deps,
        item_id,
        "classify",
        Classification,
        lambda _: _classify(deps, submission),
        lambda r: (
            "classified",
            {
                "category": r.triage.category,
                "confidence": r.triage.confidence,
                "urgency": r.triage.urgency,
                "sensitive": r.triage.sensitive,
                "invalid_output": r.invalid_output,
                "usage": r.usage.model_dump() if r.usage else None,
            },
        ),
    )
    triage = classified.triage
    enrichment = _run_step(
        deps,
        item_id,
        "enrich",
        Enrichment,
        lambda _: _enrich(deps, submission),
        lambda r: (
            "enriched",
            {
                "domain_age_days": r.domain_age_days,
                "is_free_mail": r.is_free_mail,
                "existing_contact": r.existing_contact is not None,
                "degraded": r.degraded,
            },
        ),
    )
    route = _run_step(
        deps,
        item_id,
        "route",
        Route,
        lambda _: decide_route(triage, enrichment, deps.policy),
        lambda r: ("routed", r.model_dump()),
    )

    def message(
        kind: Literal["summary", "approval_request"],
        reasons: list[str] | None = None,
        crm_contact_id: str | None = None,
    ) -> ChatMessage:
        return ChatMessage(
            item_id=item_id,
            kind=kind,
            sender=submission.name or submission.email,
            category=triage.category,
            urgency=triage.urgency,
            confidence=triage.confidence,
            summary=triage.summary,
            reasons=reasons or [],
            crm_contact_id=crm_contact_id,
        )

    if route.needs_human and not item.approved_by:
        _post_once(deps, message("approval_request", route.reasons), "post_approval_request")
        deps.store.set_status(item_id, "awaiting_approval", deps.now(), "awaiting_approval")
        return

    if route.plan == "discard":
        deps.store.set_status(item_id, "discarded", deps.now(), "discarded")
        return

    contact_id: str | None = None
    if route.plan == "crm_and_notify":
        contact = _run_step(
            deps,
            item_id,
            "crm_upsert",
            ContactResult,
            lambda _: deps.crm.upsert_contact(_contact_input(submission, triage, enrichment)),
            lambda r: ("crm_upserted", {"contact_id": r.id, "created": r.created}),
        )
        contact_id = contact.id

    _post_once(deps, message("summary", crm_contact_id=contact_id), "post_summary")
    deps.store.set_status(item_id, "done", deps.now(), "completed")


def handle_failure(item: Item, error: Exception, deps: Deps) -> None:
    now = deps.now()
    label = f"{type(error).__name__}: {error}"
    if is_retryable(error) and item.attempts < MAX_ITEM_ATTEMPTS:
        asked = error.retry_after_s if isinstance(error, HttpError) else None
        wait = max(backoff_s(item.attempts, 30.0, 1800.0, random.random), asked or 0.0)
        deps.store.retry_later(item.id, now + wait, label, now)
    else:
        deps.store.dead_letter(item.id, label, now)
        try:
            deps.chat.alert(item.id, label)
        except Exception:
            # The failure is already recorded, and an alert problem must not hide it.
            logger.exception("Could not send the failure alert for %s", item.id)


def run_once(deps: Deps) -> bool:
    """Processes one ready item. Returns False when the queue is empty."""
    item = deps.store.claim_next(deps.now(), LEASE_S)
    if item is None:
        return False
    try:
        process_item(item, deps)
    except Exception as error:
        handle_failure(item, error, deps)
    return True
