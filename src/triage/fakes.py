"""In-memory stand-ins with failure injection. Used by the tests and the demo, so the plumbing
can be proven without any accounts or network."""

from collections import deque

from triage.domain.models import (
    ChatMessage,
    Classification,
    ContactInput,
    ContactResult,
    ExistingContact,
    PostResult,
    Submission,
    Triage,
)


def triage_of(**overrides: object) -> Triage:
    values: dict[str, object] = {
        "category": "sales_lead",
        "urgency": "normal",
        "sensitive": False,
        "confidence": 0.95,
        "company": "Harborline HVAC",
        "team_size": 40,
        "budget_usd": None,
        "summary": "Wants a demo and pricing for 40 technicians.",
    }
    return Triage.model_validate({**values, **overrides})


class FakeClassifier:
    def __init__(self, *answers: Triage | Exception) -> None:
        self.answers = deque(answers)
        self.calls = 0

    def classify(self, submission: Submission) -> Classification:
        self.calls += 1
        answer = self.answers.popleft() if self.answers else triage_of()
        if isinstance(answer, Exception):
            raise answer
        return Classification(triage=answer, usage=None)


class FakeDomains:
    def __init__(self, age: int | None = 4000, error: Exception | None = None) -> None:
        self.age = age
        self.error = error

    def age_days(self, domain: str) -> int | None:
        if self.error:
            raise self.error
        return self.age


class FakeCrm:
    """Behaves like HubSpot's upsert: one contact per email, however many calls arrive."""

    def __init__(self) -> None:
        self.contacts: dict[str, dict[str, str]] = {}
        self.existing: dict[str, ExistingContact] = {}
        self.upsert_calls = 0
        self.fail_upserts: deque[Exception] = deque()
        self.crash_after_upsert: deque[Exception] = deque()

    def find_contact(self, email: str) -> ExistingContact | None:
        return self.existing.get(email)

    def upsert_contact(self, contact: ContactInput) -> ContactResult:
        self.upsert_calls += 1
        if self.fail_upserts:
            raise self.fail_upserts.popleft()
        created = contact.email not in self.contacts
        self.contacts.setdefault(contact.email, {}).update(contact.properties)
        if self.crash_after_upsert:  # the write landed, but we never heard back
            raise self.crash_after_upsert.popleft()
        return ContactResult(id=f"contact-{contact.email}", created=created)


class FakeChat:
    def __init__(self) -> None:
        self.messages: list[ChatMessage] = []
        self.resolved: list[str] = []
        self.crash_after_post: deque[Exception] = deque()
        self.fail_posts: deque[Exception] = deque()

    def post(self, message: ChatMessage) -> PostResult:
        if self.fail_posts:
            raise self.fail_posts.popleft()
        self.messages.append(message)
        if self.crash_after_post:  # the message landed, but we never heard back
            raise self.crash_after_post.popleft()
        return PostResult(ts=str(len(self.messages)))

    def find_posted(self, item_id: str, kind: str, since: float) -> PostResult | None:
        for index, message in enumerate(self.messages, start=1):
            if message.item_id == item_id and message.kind == kind:
                return PostResult(ts=str(index), recovered=True)
        return None

    def mark_resolved(self, channel: str, ts: str, text: str) -> None:
        self.resolved.append(text)
