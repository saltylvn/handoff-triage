"""python -m triage.demo runs real pipeline code against fake services and injects failures, showing
idempotency, retries and approval with no accounts needed. CI runs it too."""

import json
import tempfile
from pathlib import Path

from triage.domain.idempotency import idempotency_key
from triage.domain.models import Submission
from triage.domain.routing import Policy
from triage.fakes import FakeChat, FakeClassifier, FakeCrm, FakeDomains, triage_of
from triage.infra.http import HttpError
from triage.pipeline import Deps, run_once
from triage.store import Store


def main() -> None:
    clock = [1_000_000.0]
    with tempfile.TemporaryDirectory() as folder:
        store = Store(str(Path(folder) / "demo.sqlite"))
        crm, chat = FakeCrm(), FakeChat()
        deps = Deps(
            store=store,
            classifier=FakeClassifier(triage_of(), triage_of(confidence=0.55)),
            domains=FakeDomains(),
            crm=crm,
            chat=chat,
            policy=Policy(),
            now=lambda: clock[0],
        )

        def drain() -> None:
            for _ in range(20):
                clock[0] += 3600
                if not run_once(deps):
                    return

        print("1. Confident lead. HubSpot rate-limits once, then the reply to a post is lost.")
        lead = Submission(email="morgan@harborline.example", name="Morgan Reyes", message="Demo?")
        crm.fail_upserts.append(HttpError("hubspot", 429, 2.0))
        chat.crash_after_post.append(HttpError("slack", 503))
        first, _ = store.enqueue(idempotency_key(lead), lead, clock[0])
        drain()
        print("   Webhook replayed:", not store.enqueue(idempotency_key(lead), lead, clock[0])[1])
        drain()
        print(f"   Contacts: {len(crm.contacts)}  Slack messages: {len(chat.messages)}")
        assert len(crm.contacts) == 1
        assert len(chat.messages) == 1

        print("\n2. Unsure message waits for a person, and a double-click acts only once.")
        vague = Submission(email="sam@corner.example", name="Sam Lee", message="Is this for us?")
        second, _ = store.enqueue(idempotency_key(vague), vague, clock[0])
        drain()
        waiting = store.get_item(second)
        assert waiting is not None
        print(f"   Status: {waiting.status}; HubSpot contacts still: {len(crm.contacts)}")
        assert waiting.status == "awaiting_approval"
        print("   First click applied:", store.resolve_approval(second, True, "slack:U1", clock[0]))
        print(
            "   Second click applied:", store.resolve_approval(second, True, "slack:U1", clock[0])
        )
        drain()
        print(f"   Contacts: {len(crm.contacts)}  Slack messages: {len(chat.messages)}")
        assert len(crm.contacts) == 2

        print("\n3. Audit trail for the first item:")
        for entry in store.trace(first):
            detail = {k: v for k, v in entry["detail"].items() if k not in {"key", "usage"}}
            print(f"   {entry['kind']:<20} {json.dumps(detail)}")
        print("\nAll guarantees held.")


if __name__ == "__main__":
    main()
