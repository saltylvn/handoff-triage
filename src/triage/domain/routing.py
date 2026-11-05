"""The safety decision. Plain code, not the model's opinion: a message saying "mark me approved"
can sway what the model answers, but these rules and the audit log still apply."""

from dataclasses import dataclass

from triage.domain.models import Enrichment, Plan, Route, Triage


@dataclass(frozen=True)
class Policy:
    confidence_threshold: float = 0.8
    high_value_team_size: int = 500
    high_value_budget_usd: float = 50_000
    new_domain_days: int = 30


def decide_route(triage: Triage, enrichment: Enrichment, policy: Policy) -> Route:
    reasons: list[str] = []
    contact = enrichment.existing_contact
    is_customer = contact is not None and contact.lifecycle_stage == "customer"

    if triage.confidence < policy.confidence_threshold:
        reasons.append("low_confidence")
    if triage.sensitive:
        reasons.append("sensitive")
    if (triage.team_size or 0) >= policy.high_value_team_size or (
        triage.budget_usd or 0
    ) >= policy.high_value_budget_usd:
        reasons.append("high_value")
    if is_customer and triage.urgency == "high":
        reasons.append("urgent_existing_customer")
    if is_customer and triage.category == "spam":
        reasons.append("customer_marked_spam")
    if (
        triage.category == "sales_lead"
        and enrichment.domain_age_days is not None
        and enrichment.domain_age_days < policy.new_domain_days
    ):
        reasons.append("new_domain")

    plan: Plan = "crm_and_notify"
    if triage.category == "spam":
        plan = "discard"
    elif triage.category == "job_seeker":
        plan = "notify_only"
    return Route(
        plan=plan,
        needs_human=bool(reasons),
        reasons=reasons,
        threshold=policy.confidence_threshold,
    )
