import sqlite3

import pytest

from triage.domain.email import email_domain, is_free_mail, is_lookup_safe_domain
from triage.domain.idempotency import idempotency_key
from triage.domain.models import Enrichment, ExistingContact, Submission
from triage.domain.routing import Policy, decide_route
from triage.fakes import triage_of
from triage.store import Store


def enrichment(age: int | None = 4000, stage: str | None = None) -> Enrichment:
    contact = ExistingContact(id="1", lifecycle_stage=stage) if stage else None
    return Enrichment(
        email_domain="x.example",
        is_free_mail=False,
        domain_age_days=age,
        existing_contact=contact,
        degraded=[],
    )


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"confidence": 0.79}, "low_confidence"),
        ({"sensitive": True}, "sensitive"),
        ({"team_size": 500}, "high_value"),
        ({"budget_usd": 50_000}, "high_value"),
    ],
)
def test_risky_triage_needs_a_person(overrides: dict[str, object], reason: str) -> None:
    route = decide_route(triage_of(**overrides), enrichment(), Policy())
    assert route.needs_human
    assert reason in route.reasons


def test_threshold_is_inclusive() -> None:
    assert not decide_route(triage_of(confidence=0.8), enrichment(), Policy()).needs_human


def test_new_domain_flags_sales_only() -> None:
    assert decide_route(triage_of(), enrichment(age=5), Policy()).reasons == ["new_domain"]
    support = triage_of(category="support", team_size=None)
    assert not decide_route(support, enrichment(age=5), Policy()).needs_human


def test_urgent_customer_and_spam_customer_need_a_person() -> None:
    urgent = decide_route(triage_of(urgency="high"), enrichment(stage="customer"), Policy())
    assert urgent.reasons == ["urgent_existing_customer"]
    spam = decide_route(triage_of(category="spam"), enrichment(stage="customer"), Policy())
    assert spam.reasons == ["customer_marked_spam"]


def test_plans() -> None:
    assert decide_route(triage_of(category="spam"), enrichment(), Policy()).plan == "discard"
    assert decide_route(triage_of(category="job_seeker"), enrichment(), Policy()).plan == (
        "notify_only"
    )


def test_idempotency_key_normalizes_and_prefers_event_id() -> None:
    a = Submission(email="A@X.example", subject="Hi  there", message="Hello\n world")
    b = Submission(email="a@x.example", subject="hi there", message="hello world")
    assert idempotency_key(a) == idempotency_key(b)
    assert idempotency_key(Submission(email="a@x.example", message="m", event_id="7")) == "event:7"


def test_submission_rejects_extras_and_bad_email() -> None:
    with pytest.raises(ValueError):
        Submission.model_validate({"email": "nope", "message": "m"})
    with pytest.raises(ValueError):
        Submission.model_validate({"email": "a@x.example", "message": "m", "is_admin": True})


def test_domain_helpers() -> None:
    assert email_domain("a@B.Example") == "b.example"
    assert is_free_mail("gmail.com")
    assert is_lookup_safe_domain("acme-co.example")
    for bad in ["x/../admin", "localhost", "a b.com", "-x.com", "x.com/", "x.com?y"]:
        assert not is_lookup_safe_domain(bad)


def test_audit_log_is_append_only(store: Store) -> None:
    store.log("item", 1.0, "kind", "actor", {})
    conn = sqlite3.connect(store._path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM decisions")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE decisions SET kind='x'")
    conn.close()


def test_oauth_state_single_use_and_expiring(store: Store) -> None:
    store.save_oauth_state("abc", 100.0)
    assert not store.consume_oauth_state("wrong", 50.0)
    assert store.consume_oauth_state("abc", 50.0)
    assert not store.consume_oauth_state("abc", 50.0)
    store.save_oauth_state("late", 100.0)
    assert not store.consume_oauth_state("late", 101.0)
