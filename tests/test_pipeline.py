from conftest import World, make_world
from triage.domain.idempotency import idempotency_key
from triage.domain.models import ExistingContact, Submission
from triage.domain.ports import ModelOutputError
from triage.fakes import FakeClassifier, FakeDomains, triage_of
from triage.infra.http import HttpError
from triage.pipeline import MAX_ITEM_ATTEMPTS, run_once
from triage.store import Store

LEAD = Submission(email="Morgan@Harborline.example", name="Morgan Reyes", message="Demo please")


def submit(world: World, submission: Submission = LEAD) -> str:
    item_id, _ = world.store.enqueue(idempotency_key(submission), submission, world.clock[0])
    return item_id


def drain(world: World) -> None:
    for _ in range(30):
        world.clock[0] += 10_000  # past any retry wait
        if not run_once(world.deps):
            return


def status(world: World, item_id: str) -> str:
    item = world.store.get_item(item_id)
    assert item is not None
    return item.status


def kinds(world: World, item_id: str) -> list[str]:
    return [entry["kind"] for entry in world.store.trace(item_id)]


def test_confident_lead_runs_end_to_end(world: World) -> None:
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "done"
    assert world.crm.contacts["morgan@harborline.example"]["lifecyclestage"] == "lead"
    assert [m.kind for m in world.chat.messages] == ["summary"]
    assert kinds(world, item_id) == [
        "received",
        "classified",
        "enriched",
        "routed",
        "crm_upserted",
        "chat_posted",
        "completed",
    ]


def test_replayed_webhook_is_processed_once(world: World) -> None:
    first = submit(world)
    second = submit(world)
    drain(world)
    assert first == second
    assert world.crm.upsert_calls == 1
    assert len(world.chat.messages) == 1
    assert "duplicate_ignored" in kinds(world, first)


def test_rate_limit_retries_without_reclassifying(store: Store) -> None:
    classifier = FakeClassifier()
    world = make_world(store, classifier)
    world.crm.fail_upserts.append(HttpError("hubspot", 429, 30.0))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "done"
    assert classifier.calls == 1  # the finished step was skipped, saving quota
    assert world.crm.upsert_calls == 2


def test_retry_after_is_respected(world: World) -> None:
    world.crm.fail_upserts.append(HttpError("hubspot", 429, 500.0))
    item_id = submit(world)
    world.clock[0] += 1
    assert run_once(world.deps)
    world.clock[0] += 499
    assert run_once(world.deps) is False  # still inside the wait HubSpot asked for
    world.clock[0] += 2
    assert run_once(world.deps)
    assert status(world, item_id) == "done"


def test_lost_crm_response_leaves_one_contact(world: World) -> None:
    world.crm.crash_after_upsert.append(HttpError("hubspot", 503))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "done"
    assert world.crm.upsert_calls == 2
    assert len(world.crm.contacts) == 1


def test_lost_slack_response_does_not_post_twice(world: World) -> None:
    world.chat.crash_after_post.append(HttpError("slack", 503))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "done"
    assert len(world.chat.messages) == 1
    posted = [e for e in world.store.trace(item_id) if e["kind"] == "chat_posted"]
    assert posted[0]["detail"]["recovered"] is True


def test_worker_crash_resumes_after_lease_expires(world: World) -> None:
    item_id = submit(world)
    world.clock[0] += 1
    assert world.store.claim_next(world.clock[0], 180.0) is not None  # then the worker "dies"
    assert world.store.claim_next(world.clock[0] + 1, 180.0) is None  # lease still held
    world.clock[0] += 200
    assert run_once(world.deps)
    assert status(world, item_id) == "done"


def test_low_confidence_waits_and_writes_nothing(store: Store) -> None:
    world = make_world(store, FakeClassifier(triage_of(confidence=0.5)))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "awaiting_approval"
    assert world.crm.upsert_calls == 0
    assert [m.kind for m in world.chat.messages] == ["approval_request"]
    assert world.chat.messages[0].reasons == ["low_confidence"]


def test_approval_resumes_and_double_click_is_ignored(store: Store) -> None:
    classifier = FakeClassifier(triage_of(confidence=0.5))
    world = make_world(store, classifier)
    item_id = submit(world)
    drain(world)
    assert world.store.resolve_approval(item_id, True, "slack:U1", world.clock[0]) is True
    assert world.store.resolve_approval(item_id, True, "slack:U2", world.clock[0]) is False
    drain(world)
    assert status(world, item_id) == "done"
    assert world.crm.upsert_calls == 1
    assert classifier.calls == 1
    assert ("human_approved", "slack:U1") in [
        (e["kind"], e["actor"]) for e in world.store.trace(item_id)
    ]


def test_rejection_writes_nothing(store: Store) -> None:
    world = make_world(store, FakeClassifier(triage_of(confidence=0.5)))
    item_id = submit(world)
    drain(world)
    assert world.store.resolve_approval(item_id, False, "slack:U1", world.clock[0])
    drain(world)
    assert status(world, item_id) == "rejected"
    assert world.crm.upsert_calls == 0


def test_invalid_model_output_goes_to_a_person(store: Store) -> None:
    world = make_world(store, FakeClassifier(ModelOutputError("bad")))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "awaiting_approval"


def test_confident_spam_is_discarded_silently(store: Store) -> None:
    world = make_world(store, FakeClassifier(triage_of(category="spam", team_size=None)))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "discarded"
    assert world.crm.upsert_calls == 0
    assert world.chat.messages == []


def test_job_seeker_notifies_without_crm(store: Store) -> None:
    world = make_world(store, FakeClassifier(triage_of(category="job_seeker", team_size=None)))
    submit(world)
    drain(world)
    assert world.crm.upsert_calls == 0
    assert len(world.chat.messages) == 1


def test_failed_enrichment_does_not_block(store: Store) -> None:
    world = make_world(store, FakeClassifier(), FakeDomains(error=HttpError("rdap", 500)))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "done"
    enriched = [e for e in world.store.trace(item_id) if e["kind"] == "enriched"]
    assert enriched[0]["detail"]["degraded"] == ["domain_age"]


def test_existing_customer_keeps_lifecycle_stage(world: World) -> None:
    world.crm.existing["morgan@harborline.example"] = ExistingContact(
        id="1", lifecycle_stage="customer"
    )
    submit(world)
    drain(world)
    assert "lifecyclestage" not in world.crm.contacts["morgan@harborline.example"]


def test_permanent_error_dead_letters_immediately(world: World) -> None:
    world.crm.fail_upserts.append(HttpError("hubspot", 400))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "failed"
    assert world.crm.upsert_calls == 1


def test_repeated_outage_gives_up_visibly(world: World) -> None:
    for _ in range(MAX_ITEM_ATTEMPTS + 2):
        world.crm.fail_upserts.append(HttpError("hubspot", 503))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "failed"
    assert world.crm.upsert_calls == MAX_ITEM_ATTEMPTS
    assert "dead_lettered" in kinds(world, item_id)


def test_failure_sends_one_alert_and_can_be_requeued(world: World) -> None:
    world.crm.fail_upserts.append(HttpError("hubspot", 400))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "failed"
    assert len(world.chat.alerts) == 1
    assert world.store.requeue(item_id, "cli", world.clock[0]) is True
    assert world.store.requeue(item_id, "cli", world.clock[0]) is False  # no longer failed
    drain(world)
    assert status(world, item_id) == "done"
    assert world.crm.upsert_calls == 2
    assert "requeued" in kinds(world, item_id)


def test_a_broken_alert_does_not_hide_the_failure(world: World) -> None:
    world.chat.fail_alerts = True
    world.crm.fail_upserts.append(HttpError("hubspot", 400))
    item_id = submit(world)
    drain(world)
    assert status(world, item_id) == "failed"
    assert "dead_lettered" in kinds(world, item_id)


def test_requeue_ignores_items_that_did_not_fail(world: World) -> None:
    item_id = submit(world)
    assert world.store.requeue(item_id, "cli", world.clock[0]) is False
